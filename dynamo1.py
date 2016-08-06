import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('fillups', global_secondary_indexes=['Date-index'])
response = table.scan()

for item in response['Items']:
    # print item
    for key, value in item.items():
        print key, value
    print '\n\n'
