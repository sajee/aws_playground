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

'''
Per instance, display volumes with no snapshots or
volumes that have not been snapshotted recently.
'''

import boto3
import botocore

from datetime import datetime, timedelta
import time

INSTANCE_NAME_TAG = 'Name'
SNAPSHOT_AGE_IN_HOURS = 24
SLEEP_IN_SECONDS = 5

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
                    print("Volume ID: %s" % (volume.id))
                    snapshot_taken = False

                    for snapshot in volume.snapshots.all():
                        snapshot_taken = True
                        snapshot_date = snapshot.start_time
                        print(': Snapshot:' + snapshot.id + "  " + str(snapshot_date), end = '')
                        # Can't compare TZ naive datatime.now to TZ aware snapshot date.
                        # Removed timezone from snapshot timestamp (which is UTC).   Compare against current UTC time.
                        snapshot_out_of_date = snapshot_date.replace(tzinfo=None) < datetime.utcnow() - timedelta(
                            hours=SNAPSHOT_AGE_IN_HOURS)
                        snapshot_delta = datetime.utcnow().replace(microsecond=0) - snapshot_date.replace(tzinfo=None).replace(
                            microsecond=0)
                        snapshot_age_msg = str(snapshot_delta) + " since last snapshot."

                        if snapshot_out_of_date:
                            print("\t*** WARNING: This snapshot is out of date.\t" + snapshot_age_msg)
                        else:
                            print("\t@@@ This snapshot is current.\t\t\t\t" + snapshot_age_msg)

                    if not snapshot_taken:
                        print(":\t *** WARNING: No snapshots taken for this volume.")

            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'RequestLimitExceeded':
                    #print("^^^^^^^^^^   REQUEST LIMIT EXCEEDED ^^^^^^^^^^^^^: %s" % e)
                    time.sleep(SLEEP_IN_SECONDS) # boto's built-in exponential backoff wasn't good enough so just sleep
                else:
                    print("%%%%%%%%%%%%%%%%%%%% Unexpected error: %s" % e)
                continue
            break



check_volumes()
