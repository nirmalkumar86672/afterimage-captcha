"""Shared immutable records, atomic redemption and hourly issuance quotas."""
import json, os, sqlite3, time
from pathlib import Path

class SQLiteStore:
    def __init__(self,path):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.path=str(path)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS records (pk TEXT PRIMARY KEY, payload TEXT NOT NULL, expires INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS counters (pk TEXT PRIMARY KEY, n INTEGER NOT NULL, expires INTEGER NOT NULL)')
    def connect(self): return sqlite3.connect(self.path,timeout=15)
    def put(self,key,value,expires=0):
        with self.connect() as db:
            db.execute('DELETE FROM records WHERE expires>0 AND expires<=?',(int(time.time()),))
            db.execute('INSERT INTO records VALUES (?,?,?)',(key,json.dumps(value),expires))
    def get(self,key):
        with self.connect() as db:
            row=db.execute('SELECT payload,expires FROM records WHERE pk=?',(key,)).fetchone()
        return json.loads(row[0]) if row and (not row[1] or row[1]>time.time()) else None
    def take(self,key):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT payload,expires FROM records WHERE pk=?',(key,)).fetchone()
            db.execute('DELETE FROM records WHERE pk=?',(key,))
        return json.loads(row[0]) if row and row[1]>time.time() else None
    def count(self,key,limit,expires):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM counters WHERE expires<=?',(int(time.time()),))
            row=db.execute('SELECT n FROM counters WHERE pk=?',(key,)).fetchone()
            if row and row[0]>=limit:return False
            db.execute('INSERT INTO counters VALUES (?,1,?) ON CONFLICT(pk) DO UPDATE SET n=n+1',(key,expires))
        return True

class DynamoStore:
    def __init__(self,table):
        import boto3
        self.table=boto3.resource('dynamodb',region_name=os.getenv('AWS_REGION','ap-south-1')).Table(table)
    def put(self,key,value,expires=0):
        item={'pk':key,'payload':json.dumps(value)}
        if expires:item['expires']=expires
        self.table.put_item(Item=item,ConditionExpression='attribute_not_exists(pk)')
    def get(self,key):
        item=self.table.get_item(Key={'pk':key},ConsistentRead=True).get('Item')
        return json.loads(item['payload']) if item and item.get('expires',time.time()+1)>time.time() else None
    def take(self,key):
        from botocore.exceptions import ClientError
        try:
            item=self.table.delete_item(Key={'pk':key},ConditionExpression='attribute_exists(pk) AND expires > :now',ExpressionAttributeValues={':now':int(time.time())},ReturnValues='ALL_OLD').get('Attributes')
            return json.loads(item['payload']) if item else None
        except ClientError as e:
            if e.response['Error']['Code']=='ConditionalCheckFailedException':return None
            raise
    def count(self,key,limit,expires):
        from botocore.exceptions import ClientError
        try:
            self.table.update_item(Key={'pk':key},UpdateExpression='SET expires = :expiry ADD #n :one',ConditionExpression='attribute_not_exists(#n) OR #n < :limit',ExpressionAttributeNames={'#n':'count'},ExpressionAttributeValues={':one':1,':limit':limit,':expiry':expires})
            return True
        except ClientError as e:
            if e.response['Error']['Code']=='ConditionalCheckFailedException':return False
            raise

def configured_store():
    table=os.getenv('DYNAMODB_TABLE')
    if table:return DynamoStore(table)
    if os.getenv('APP_ENV')=='production':raise RuntimeError('Production requires DYNAMODB_TABLE')
    return SQLiteStore(os.getenv('SQLITE_PATH','.local/service.db'))
