import MySQLdb
import _mysql_exceptions
from _mysql_exceptions import OperationalError
import argparse
import sys
import os.path

def get_args():
    desc = "Stage Vs Production"
    epilog = """
Examples:
    python schema-compare.py -c localhost -u root -p password -f1 file1.sql -f2 file2.sql
"""
    parser = argparse.ArgumentParser(description=desc,epilog=epilog,
                                    formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-c', '--client',
                       help='Host of the db',
                       required=True)

    parser.add_argument('-u', '--user',
                       help='User Of db',
                       required=True)

    parser.add_argument('-p', '--passwd',
                       help="Password of the user's database",
                       required=True)

    parser.add_argument('-f1', '--file1',
                       help="Stage server dump file",
                       required=True)

    parser.add_argument('-f2', '--file2',
                       help="Production server dump file",
                       required=True)

    ret = parser.parse_args()
    return ret

def get_connection(client, user, passwd):
	
	try:
		return MySQLdb.connect(host=client, user=user, passwd=passwd)
	except MySQLdb.Error as e:
		print("Something went wrong:")
		print(e)
		sys.exit()

def import_into_db(cur, dbName, filename):
	try: 
		cmd = 'create database ' + dbName + ';'
		cur.execute(cmd)
		cmd = 'use ' + dbName + ';'
		cur.execute(cmd)
		fd = open(filename, 'r')
		sqlFile = fd.read()
		fd.close()
		sqlCommands = sqlFile.split(';')
	except Exception as e:
		print e
		close_connection()
		sys.exit()
	for command in sqlCommands:
	    try:
	        cur1.execute(command)
	    except OperationalError, msg:
	        print "Command skipped: ", msg
	        close_connection()
	        sys.exit()

def fetchTableName(cur, dbName):
	cmd = 'use ' + dbName + ';'
	cur.execute(cmd)
	cur.execute('show tables;')
	tableName = cur.fetchall()
	return tableName
	
def checkMissingTable(db1, db2):
	l1 = len(db1)
	l2 = len(db2)
	missingStageTable = []
	missingProductionTable = []
	commonTable = []
	for table in db1:
		if table in db2:
			commonTable.append(table)
		else:
			missingProductionTable.append(table)
	for table in db2:
		if table in db1:
			continue
		else:
			missingStageTable.append(table)
	return missingStageTable, missingProductionTable, commonTable

def checkMissingColumn(tempCur1, tempCur2, tableName, db1, db2):
	cmd1 = "select COLUMN_NAME from INFORMATION_SCHEMA.COLUMNS where TABLE_NAME='"+ tableName + "' AND  TABLE_SCHEMA='"+ db1 + "' ;"
	cmd2 = "select COLUMN_NAME from INFORMATION_SCHEMA.COLUMNS where TABLE_NAME='"+ tableName + "' AND  TABLE_SCHEMA='"+ db2+ "' ;"
	tempCur1.execute(cmd1)
	tempCur2.execute(cmd2)
	tempList1 = tempCur1.fetchall()
	tempList2 = tempCur2.fetchall()
	missingColStage = []
	missingColProduction = []
	for row in tempList1:
		if row in tempList2:
			continue
		else:
			missingColProduction.append(row[0])
	for row in tempList2:
		if row in tempList1:
			continue
		else:
			missingColStage.append(row[0])

	return missingColStage, missingColProduction

def tableSync():
	stageDB = []
	productionDB = []
	tableName1 = fetchTableName(cur1, 'stage')
	for row in tableName1:
	    stageDB.append(row[0])
	tableName2 = fetchTableName(cur2, 'prod')
	for row in tableName2:
	    productionDB.append(row[0])
	missingInStage, missingInProduction, commonTable = checkMissingTable(stageDB, productionDB)
	if len(missingInStage) > 0 or len(missingInProduction) > 0:
		print '#############################################'
		print '############Table Synchronization############'
		print '#############################################'
	if len(missingInStage) > 0 :
		print 'Missing table in Stage Server are : '
		print missingInStage

	if len(missingInProduction) > 0 :
		print 'Missing table in Production Server are : '
		print missingInProduction
	return commonTable

def columnSync(commonTable):
	for table in commonTable:
		stageCol, productionCol = checkMissingColumn(cur1, cur2, table, 'stage', 'prod') 
		if len(stageCol) > 0 or len(productionCol) > 0:
			print '#############################################'
			print '############Column Synchronization###########'
			print '#############################################'
			print 'For Table : {}'.format(table)
		if len(stageCol) > 0:
			print 'Missing Columns in Stage Server are : '
			print stageCol
		if len(productionCol) > 0:
			print 'Missing Columns in Production Server are : '
			print productionCol


def close_connection():
	try:
		cur1.execute('drop database stage;')
		cur2.execute('drop database prod;')
		cur1.close()
		cur2.close()
		db.close()
	except Exception as e:
		sys.exit()

if __name__ == '__main__':
	global args, db, cur1, cur2

	args = get_args()
	client = args.client; user = args.user; passwd = args.passwd
	file1 = args.file1; file2 = args.file2
	if os.path.isfile(file1) == False:
		print 'Stage db dump file does not exist'
		sys.exit()
	if os.path.isfile(file2) == False:
		print 'Production db dump file does not exist'
		sys.exit()
	db = get_connection(client, user, passwd)

	cur1 = db.cursor()
	cur2 = db.cursor()

	import_into_db(cur1, 'stage', file1)
	import_into_db(cur2, 'prod', file2)

	commonTable = tableSync()
	columnSync(commonTable)

	close_connection()
