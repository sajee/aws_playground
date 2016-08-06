'''
Display instances that have volumes that have no snapshots or
volumes that have not been snapshotted recently.
'''

import boto3
from datetime import datetime, timedelta

ec2 = boto3.resource('ec2')
ec2_client = boto3.client('ec2')

instance_name_tag = 'Name'
instances = ec2.instances.filter()
for instance in instances:
    print("\n")
    instance_name = ''
    for tag in instance.tags:
        instance_name = tag['Value'] if tag['Key'] == instance_name_tag else None
    print("Instance name: '%s' \t Instance ID: %s." %(instance_name, instance.id))
    for mapping in instance.block_device_mappings:
        volume = mapping['Ebs']
        print("Volume ID: %s" % (volume["VolumeId"]))
        snapshot_data = ec2_client.describe_snapshots(Filters=[{'Name': 'volume-id', 'Values': [volume["VolumeId"]]}])
        snapshots = snapshot_data["Snapshots"]

        if not snapshots:
            print(":\t *** WARNING: No snapshots taken for this volume.")
        else:
            for snapshot in snapshots:
                snapshot_date = snapshot['StartTime']
                print(': Snapshot:' + snapshot['SnapshotId'] + "  " + str(snapshot_date), end = '')
                snapshot_older_than_a_day = snapshot_date.replace(tzinfo=None) < datetime.now() - timedelta(days=1)
                if snapshot_older_than_a_day:
                    print("\t*** WARNING: This snapshot is out of date.")
