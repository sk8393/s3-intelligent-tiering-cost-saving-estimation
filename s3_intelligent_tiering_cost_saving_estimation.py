import boto3
import json

from datetime import datetime

def get_bucket_name_list():
    client = boto3.client('s3')
    response = client.list_buckets()
    # print("response = {}".format(response))
    bucket_list = response.get('Buckets', [])
    bucket_name_list = list()
    for _i in bucket_list:
        bucket_name_list.append(_i['Name'])
    # print("bucket_name_list = {}".format(bucket_name_list))
    return bucket_name_list

def get_object_list(_arg_bucket_name):
    content_list = list()
    client = boto3.client('s3')
    paginator = client.get_paginator('list_objects_v2')
    page_list = paginator.paginate(Bucket=_arg_bucket_name)
    count = 0
    for _i in page_list:
        count += 1
        content_list += _i.get('Contents', [])
        if count % 100 == 0:
            print("Pagination required for S3 bucket {}, currently {}.".format(_arg_bucket_name, count))
    return content_list

def get_bucket_region(_arg_bucket_name):
    client = boto3.client('s3')
    response = client.head_bucket(Bucket=_arg_bucket_name)
    # print("response = {}".format(response))
    bucket_region = response['ResponseMetadata']['HTTPHeaders']['x-amz-bucket-region']
    return bucket_region

def get_bucket_statistical_data(_arg_bucket_name):
    object_list =  get_object_list(_arg_bucket_name)
    total_object_count = 0
    total_object_size = 0
    total_object_over_128_kbytes_count = 0
    total_object_over_128_kbytes_size = 0
    for _i in object_list:
        # print("_i = {}".format(_i))
        storage_class = _i['StorageClass']
        size = _i['Size']
        total_object_count += 1
        total_object_size += size
        if storage_class == 'STANDARD':
            if size > 128 * 1024:
                total_object_over_128_kbytes_count += 1
                total_object_over_128_kbytes_size += size
            else:
                pass
        else:
            pass

    bucket_region = get_bucket_region(_arg_bucket_name)

    bucket_statistical_data = {
        'bucket_name': _arg_bucket_name,
        'bucket_region': bucket_region,
        'total_object_count': total_object_count,
        'total_object_size': total_object_size,
        'total_object_over_128_kbytes_count': total_object_over_128_kbytes_count,
        'total_object_over_128_kbytes_size': total_object_over_128_kbytes_size
    }

    return bucket_statistical_data

def get_values_from_nested_dict(data, target_key):
    result = []

    if isinstance(data, dict):
        for key, value in data.items():
            if key == target_key:
                if isinstance(value, list):
                    result.extend(value)
                else:
                    result.append(value)
            elif isinstance(value, dict):
                result.extend(get_values_from_nested_dict(value, target_key))
    return result

def get_price_per_unit(_arg_filter_list):
    price_list = list()
    client = boto3.client('pricing', region_name='us-east-1')
    paginator = client.get_paginator('get_products')
    # Assume that only one price item returns with following API.
    page_list = paginator.paginate(
        ServiceCode = 'AmazonS3',
        Filters = _arg_filter_list
    )
    for _i_page in page_list:
        price_list += _i_page.get('PriceList', [])
    # print("price_list = {}".format(price_list))
    len_price_list = len(price_list)
    if len_price_list != 1:
        exit()
    price_str = price_list[0]
    price_json = json.loads(price_str)
    # print("price_json = {}".format(price_json))
    # For example, S3 Intelligent Tiering - Frequent Access Tier has 3 pricing tiers (e.g. Frequent Access Tier, First 50 TB/Month $0.023 per GB) according to total object size.
    # There are three pricing data in single item, so need to check three values of 'pricePerUnit'.
    price_per_unit_dict_list = get_values_from_nested_dict(price_json, 'pricePerUnit')
    # print("price_per_unit_dict_list = {}".format(price_per_unit_dict_list))
    price_per_unit_value_list = list()
    for _i in price_per_unit_dict_list:
        price = float(_i.get('USD', 0))
        price_per_unit_value_list.append(price)
    # Adapt the most expensive one in case there are multiple prices for single pricing item.
    # Frequent Access Tier, First 50 TB/Month $0.0245 per GB
    # Frequent Access Tier, Next 450 TB/Month $0.0235 per GB
    # Frequent Access Tier, Over 500 TB/Month $0.0225 per GB
    price_per_unit = max(price_per_unit_value_list)
    return price_per_unit

def get_intelligent_tiering_frequent_access_tier_per_gbyte_per_month_usd(_arg_bucket_region):
    filter_list = [
        {'Type':'TERM_MATCH','Field':'regionCode','Value': _arg_bucket_region},
        {'Type':'TERM_MATCH','Field':'storageClass','Value':'Intelligent-Tiering'},
        {'Type':'TERM_MATCH','Field':'termType','Value':'OnDemand'},
        {'Type':'TERM_MATCH','Field':'volumeType','Value':'Intelligent-Tiering Frequent Access'}
    ]
    price_per_unit = get_price_per_unit(filter_list)
    return price_per_unit

def get_intelligent_tiering_archive_instant_access_tier_per_gbyte_per_month_usd(_arg_bucket_region):
    filter_list = [
        {'Type':'TERM_MATCH','Field':'regionCode','Value': _arg_bucket_region},
        {'Type':'TERM_MATCH','Field':'storageClass','Value':'Intelligent-Tiering'},
        {'Type':'TERM_MATCH','Field':'termType','Value':'OnDemand'},
        {'Type':'TERM_MATCH','Field':'volumeType','Value':'Intelligent-Tiering Archive Instant Access'}
    ]
    price_per_unit = get_price_per_unit(filter_list)
    return price_per_unit

def get_intelligent_tiering_monitoring_and_automation_per_1000_objects_usd(_arg_bucket_region):
    filter_list = [
        {'Type':'TERM_MATCH','Field':'feeCode','Value':'S3-Monitoring and Automation-ObjectCount'},
        {'Type':'TERM_MATCH','Field':'regionCode','Value': _arg_bucket_region},
        {'Type':'TERM_MATCH','Field':'termType','Value':'OnDemand'}
    ]
    price_per_unit = get_price_per_unit(filter_list)
    # Need to multiple with 1000 to make this as per 1000 objects.
    return price_per_unit * 1000

def get_saving_effect(_arg_bucket_statistical_data):
    bucket_region = _arg_bucket_statistical_data.get('bucket_region')
    # print("bucket_region = {}".format(bucket_region))

    intelligent_tiering_frequent_access_tier_per_gbyte_per_month_usd = get_intelligent_tiering_frequent_access_tier_per_gbyte_per_month_usd(bucket_region)
    intelligent_tiering_archive_instant_access_tier_per_gbyte_per_month_usd = get_intelligent_tiering_archive_instant_access_tier_per_gbyte_per_month_usd(bucket_region)
    intelligent_tiering_monitoring_and_automation_per_1000_objects_usd = get_intelligent_tiering_monitoring_and_automation_per_1000_objects_usd(bucket_region)

    total_object_over_128_kbytes_count = _arg_bucket_statistical_data.get('total_object_over_128_kbytes_count', 0)
    total_object_over_128_kbytes_size = _arg_bucket_statistical_data.get('total_object_over_128_kbytes_size', 0)

    yearly_monitoring_fee_usd = total_object_over_128_kbytes_count / 1000 * intelligent_tiering_monitoring_and_automation_per_1000_objects_usd * 12
    yearly_cost_saving_of_storage_usd = total_object_over_128_kbytes_size / 1024 / 1024 / 1024 * (intelligent_tiering_frequent_access_tier_per_gbyte_per_month_usd - intelligent_tiering_archive_instant_access_tier_per_gbyte_per_month_usd) * 12

    yearly_cost_saving_usd = yearly_cost_saving_of_storage_usd - yearly_monitoring_fee_usd

    saving_effect = _arg_bucket_statistical_data
    saving_effect['intelligent_tiering_frequent_access_usd'] = intelligent_tiering_frequent_access_tier_per_gbyte_per_month_usd
    saving_effect['intelligent_tiering_archive_instant_access_usd'] = intelligent_tiering_archive_instant_access_tier_per_gbyte_per_month_usd
    saving_effect['intelligent_tiering_monitoring_usd'] = intelligent_tiering_monitoring_and_automation_per_1000_objects_usd
    saving_effect['yearly_cost_saving_usd'] = round(yearly_cost_saving_usd, 2)
    return saving_effect

def get_aws_account_id():
    client = boto3.client('sts')
    account_id = client.get_caller_identity()["Account"]
    return account_id

def put_result_csv(_arg_saving_effect_list):
    result_csv = 'account_id,bucket,region,intelligent_tiering_frequent_access_usd,intelligent_tiering_archive_instant_access_usd,intelligent_tiering_monitoring_usd,total_object_count,total_object_size,total_object_over_128_kbytes_count,total_object_over_128_kbytes_size,yearly_cost_saving_usd'
    for _i in _arg_saving_effect_list:
        result = "{},{},{},{},{},{},{},{},{},{},{}".format(
            get_aws_account_id(),
            _i['bucket_name'],
            _i['bucket_region'],
            _i['intelligent_tiering_frequent_access_usd'],
            _i['intelligent_tiering_archive_instant_access_usd'],
            _i['intelligent_tiering_monitoring_usd'],
            _i['total_object_count'],
            _i['total_object_size'],
            _i['total_object_over_128_kbytes_count'],
            _i['total_object_over_128_kbytes_size'],
            _i['yearly_cost_saving_usd']
        )
        result_csv = result_csv + '\n' + result
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d-%H:%M:%S")
    csv_file = "s3_intelligent_tiering_cost_saving_estimation_{}.csv".format(current_time)
    with open(csv_file, 'w') as file:
        file.write(result_csv)

if __name__ == '__main__':
    bucket_name_list = get_bucket_name_list()

    # # Set specific bucket for test.
    # bucket_name_list = ['example-bucket']

    print("bucket_name_list = {}".format(bucket_name_list))

    saving_effect_list = list()

    for _i_bucket_name in bucket_name_list:
        print("_i_bucket_name = {}".format(_i_bucket_name))
        bucket_statistical_data = get_bucket_statistical_data(_i_bucket_name)
        # print("bucket_statistical_data = {}".format(bucket_statistical_data))
        saving_effect = get_saving_effect(bucket_statistical_data)
        print("saving_effect = {}".format(saving_effect))
        saving_effect_list.append(saving_effect)

    put_result_csv(saving_effect_list)
