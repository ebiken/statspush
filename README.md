# statspush
Collect stats and push to places like AWS S3.

## Setup AWS

If you want to push to AWS S3, instal Boto 3 and Setup AWS credentials / default region.

* Install boto

```
$ sudo pip install boto3
```

* Setup AWS credentials and default region.

```
$ cat ~/.aws/credentials
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
$ cat ~/.aws/config
[default]
region=ap-northeast-1
```

