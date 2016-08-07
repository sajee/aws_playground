'''
Display instances that have volumes that have no snapshots or
volumes that have not been snapshotted recently.
'''

import boto3
from datetime import datetime, timedelta

ec2 = boto3.resource('ec2')

instance_name_tag = 'Name'
instances = ec2.instances.all() # .filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
for instance in instances:
    print("\n")
    instance_name = ''
    for tag in instance.tags:
        instance_name = tag['Value'] if tag['Key'] == instance_name_tag else None
    print("Instance name: '%s' \t Instance ID: %s." %(instance_name, instance.id))

    for volume in instance.volumes.all():
        print("Volume ID: %s" % (volume.id))
        snapshot_taken =  False

        for snapshot in volume.snapshots.all():
            snapshot_taken = True
            snapshot_date = snapshot.start_time
            print(': Snapshot:' + snapshot.id+ "  " + str(snapshot_date), end = '')
            # FIX: datatime.now doesn't have TZ info which causes an error when compared to snapshot date.
            # Removed timezone foe now.  Need to fix.
            snapshot_older_than_a_day = snapshot_date.replace(tzinfo=None) < datetime.now() - timedelta(days=1)
            if snapshot_older_than_a_day:
                print("\t*** WARNING: This snapshot is out of date.")
        if not snapshot_taken:
            print(":\t *** WARNING: No snapshots taken for this volume.")
