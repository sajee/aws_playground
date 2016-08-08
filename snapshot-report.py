'''
Per instance, display volumes with no snapshots or
volumes that have not been snapshotted recently.
'''

import boto3
from datetime import datetime, timedelta

ec2 = boto3.resource('ec2')

INSTANCE_NAME_TAG = 'Name'
SNAPSHOT_AGE_IN_HOURS = 24

instances = ec2.instances.all() # .filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
for instance in instances:
    instance_name = ''
    for tag in instance.tags:
        instance_name = tag['Value'] if tag['Key'] == INSTANCE_NAME_TAG else None
    print("\n\nInstance name: '%s' \t Instance ID: %s" %(instance_name, instance.id))

    for volume in instance.volumes.all():
        print("Volume ID: %s" % (volume.id))
        snapshot_taken =  False

        for snapshot in volume.snapshots.all():
            snapshot_taken = True
            snapshot_date = snapshot.start_time
            print(': Snapshot:' + snapshot.id+ "  " + str(snapshot_date), end = '')
            # Can't compare TZ naive datatime.now to TZ aware snapshot date.
            # Removed timezone from snapshot timestamp (which is UTC).   Compare against current UTC time.
            snapshot_out_of_date = snapshot_date.replace(tzinfo=None) < datetime.utcnow() - timedelta(hours=SNAPSHOT_AGE_IN_HOURS)
            snapshot_delta = datetime.utcnow().replace(microsecond=0) - snapshot_date.replace(tzinfo=None).replace(microsecond=0)
            snapshot_age_msg = str(snapshot_delta) + " since last snapshot."

            if snapshot_out_of_date:
                print("\t*** WARNING: This snapshot is out of date.\t" + snapshot_age_msg)
            else:
                print("\t@@@ This snapshot is current.\t\t\t\t" + snapshot_age_msg)
        if not snapshot_taken:
            print(":\t *** WARNING: No snapshots taken for this volume.")
