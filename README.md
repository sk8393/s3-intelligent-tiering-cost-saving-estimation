# S3 Intelligent-Tiering Cost Saving Estimation

## Description
[Amazon Simple Storage Service (S3) Intelligent-Tiering](https://aws.amazon.com/s3/storage-classes/intelligent-tiering/) is designed to optimize storage costs by automatically moving data between multiple access tiers.  Less frequently accessed objects will be moved to colder tier which has smaller per Gigabyte storage cost.

S3 Intelligent-Tiering deserves to be the default storage class when using S3.  Because the default three access tiers, 1/ **Frequent Access Tier**, 2/ **Infrequent Access Tier**, and 3/ **Archive Instant Access Tier**, provide low latency access to the objects, and there is no fee for moving objects between tiers and retrieval of the data.  Just to be sure, there is a monitoring fee for objects bigger than 128 Kilobytes ($0.0025 per 1,000 objects).

If you are considering migration of objects stored in **Standard** storage class to **Intelligent-Tiering**, the cost reduction amount will be a factor in deciding whether to migrate.  You can check the total object size for each storage class from [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) Metric **BucketSizeBytes**, but **Intelligent-Tiering** only moves objects that are bigger than 128 Kilobytes between access tiers.  This script scans all S3 buckets in the AWS account, identifies objects larger than 128 Kilobytes, and calculates the annual cost savings.  Specifically, the script calculates the cost reduction when **Standard** objects bigger than 128 Kilobytes are migrated to **Intelligent-Tiering's Archive Instant Access Tier**, then deducts the monitoring fee.

## Usage
With [AWS CloudShell](https://aws.amazon.com/cloudshell/), you can just clone this repository and run the Python script as below.  To scan all objects in each bucket, it can take a few minutes for completion.

```
$ git clone https://github.com/sk8393/s3-intelligent-tiering-cost-saving-estimation.git
$ cd s3-intelligent-tiering-cost-saving-estimation
$ python3 s3_intelligent_tiering_cost_saving_estimation.py
```

Once the script completes, a csv file will be generated in the same directory as Python script.  A sample output is included in this repository.

## Support
This sample was tested that the expected results were obtained in an actual AWS account.  It is implemented so that no changes are made to your resources, but we recommend that you try it once in a test environment when using it.
