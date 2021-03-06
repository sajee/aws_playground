# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import boto3
import botocore

from datetime import datetime, timedelta
import time

INSTANCE_NAME_TAG = 'Name'
SNAPSHOT_AGE_IN_HOURS = 24
SLEEP_IN_SECONDS = 5


def instances_and_volumes(region_name):
    while True:
        try:
            ec2 =  boto3.client('ec2', region_name=region_name)
            instances_paginator = ec2.get_paginator('describe_instances')
            #volumes_paginator = ec2.get_paginator('describe_volumes')

            for instances_page in instances_paginator.paginate():
                for instance in instances_page['Reservations']:
                    for i in instance['Instances']:
                        print('\n%s,%s' %(region_name, i['InstanceId']), end='')
                        for bdm in i['BlockDeviceMappings']:
                            print(', %s ' %bdm['Ebs']['VolumeId'], end='')

        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'RequestLimitExceeded':
                print("^^^^^^^^^^   REQUEST LIMIT EXCEEDED ^^^^^^^^^^^^^: %s" % e)
                time.sleep(SLEEP_IN_SECONDS)  # boto's built-in exponential backoff expired so just sleep
            else:
                print("%%%%%%%%%%%%%%%%%%%% Unexpected error: %s" % e)
            continue
        break


'''
Per instance, display volumes with no snapshots or
volumes that have not been snapshotted recently.
'''
def report_by_volumes(region_name):
    while True:  # in case of an exception, redo volume or snapshot check.  See http://stackoverflow.com/questions/2083987/how-to-retry-after-exception-in-python
        try:
            ec2 = boto3.client('ec2', region_name=region_name)
            volumes_paginator = ec2.get_paginator('describe_volumes')
            snapshots_paginator = ec2.get_paginator('describe_snapshots')

            for page in volumes_paginator.paginate():
                for volume in page['Volumes']:
                    time_since_latest_snapshot = timedelta.max
                    instance_id = volume['Attachments'][0]['InstanceId'] if volume['Attachments'] else 'Unattached'
                    volume_id, az = volume['VolumeId'], volume['AvailabilityZone']
                    print('%s attached to %s in %s\t\t\t' % (volume_id, instance_id, az), end='')
                    snapshots_iterator = snapshots_paginator.paginate(OwnerIds=['self'], Filters=[{'Name': 'volume-id', 'Values': [volume_id]}])
                    snapshot_taken = False

                    for snapshots in snapshots_iterator:
                        for snapshot in snapshots['Snapshots']:
                            snapshot_taken = True
                            snapshot_date = snapshot['StartTime']
                            time_since_snapshot = datetime.utcnow().replace(microsecond=0) - snapshot_date.replace(
                                tzinfo=None).replace(microsecond=0)
                            if time_since_snapshot < time_since_latest_snapshot:
                                time_since_latest_snapshot = time_since_snapshot
                                latest_snapshot = snapshot

                            snapshot_age_msg = str(time_since_latest_snapshot) + " elapsed since last snapshot %s." % (snapshot['SnapshotId'])

                    if not snapshot_taken:
                        print("\t*** WARNING: No snapshots taken for this volume.")
                    else:
                        snapshot_out_of_date = latest_snapshot['StartTime'].replace(
                            tzinfo=None) < datetime.utcnow() - timedelta(
                            hours=SNAPSHOT_AGE_IN_HOURS)
                        if snapshot_out_of_date:
                            print("\t### WARNING: It's been %s" % snapshot_age_msg)
                        else:
                            print(
                                "\t@@@ %s is the latest snapshot for this volume and it's current. " % latest_snapshot[
                                    'SnapshotId'],
                                snapshot_age_msg)

        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'RequestLimitExceeded':
                print("^^^^^^^^^^   REQUEST LIMIT EXCEEDED ^^^^^^^^^^^^^: %s" % e)
                time.sleep(SLEEP_IN_SECONDS)  # boto's built-in exponential backoff expired so just sleep
            else:
                print("%%%%%%%%%%%%%%%%%%%% Unexpected error: %s" % e)
            continue
        break


def check_volumes():
    ec2 = boto3.resource('ec2')

    instances = ec2.instances.all()  # .filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    for instance in instances:
        instance_name = ''
        for tag in instance.tags:
            instance_name = tag['Value'] if tag['Key'] == INSTANCE_NAME_TAG else None

        print("\n\nInstance name: '%s' \t Instance ID: %s" % (instance_name, instance.id))

        while True:  # in case of an exception, redo volume or snapshot check.  See http://stackoverflow.com/questions/2083987/how-to-retry-after-exception-in-python
            try:
                for volume in instance.volumes.all():
                    print("Volume ID: %s\t" % (volume.id), end = '')
                    snapshot_taken = False
                    time_since_latest_snapshot = timedelta.max
                    latest_snapshot = None

                    for snapshot in volume.snapshots.all():
                        snapshot_taken = True
                        snapshot_date = snapshot.start_time

                        time_since_snapshot = datetime.utcnow().replace(microsecond=0) - snapshot_date.replace(tzinfo=None).replace(
                            microsecond=0)
                        if time_since_snapshot < time_since_latest_snapshot:
                            time_since_latest_snapshot = time_since_snapshot
                            latest_snapshot = snapshot

                        snapshot_age_msg = str(time_since_latest_snapshot) + " elapsed since last snapshot."

                    if not snapshot_taken:
                        print("\t*** WARNING: No snapshots taken for this volume.")
                    else:
                        snapshot_out_of_date = latest_snapshot.start_time.replace(tzinfo=None) < datetime.utcnow() - timedelta(
                            hours=SNAPSHOT_AGE_IN_HOURS)
                        if snapshot_out_of_date:
                            print("\t### WARNING: It's been %s" % snapshot_age_msg)
                        else:
                            print("\t@@@ %s is the latest snapshot for this volume and it's current. " %  latest_snapshot.id, snapshot_age_msg)

            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'RequestLimitExceeded':
                    #print("^^^^^^^^^^   REQUEST LIMIT EXCEEDED ^^^^^^^^^^^^^: %s" % e)
                    time.sleep(SLEEP_IN_SECONDS) # boto's built-in exponential backoff wasn't good enough so just sleep
                else:
                    print("%%%%%%%%%%%%%%%%%%%% Unexpected error: %s" % e)
                continue
            break


def main():
    ec2 = boto3.client('ec2')

    regions = ec2.describe_regions()
    for region in regions['Regions']:
        #instances_and_volumes(region['RegionName'])
        report_by_volumes(region['RegionName'])
        #check_volumes()

if __name__ == "__main__":
    main()