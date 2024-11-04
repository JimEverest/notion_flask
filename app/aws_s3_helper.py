import os
import json
import datetime
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from typing import List, Optional



class S3Client:
    """
    S3Client 封装了与 Amazon S3 的常用操作。
    """

    def __init__(self, config_path: str):
        # 加载配置文件
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)

        # 提取 AWS 凭证
        aws_access_key_id = config.get('aws', {}).get('access_key_id')
        aws_secret_access_key = config.get('aws', {}).get('secret_access_key')
        bucket_name = config.get('aws', {}).get('bucket_name')
        region = config.get('aws', {}).get('region', 'us-east-1')

        if not all([aws_access_key_id, aws_secret_access_key, bucket_name]):
            raise ValueError("配置文件中缺少必要的 AWS 凭证或存储桶名称。")

        # 初始化 S3 客户端
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region
        )
        self.bucket_name = bucket_name

    def upload_file(self, local_file: str, object_name: str = None):
        if object_name is None:
            object_name = local_file
        try:
            self.s3_client.upload_file(local_file, self.bucket_name, object_name)
            print(f"文件 '{local_file}' 成功上传到存储桶 '{self.bucket_name}'，对象名为 '{object_name}'。")
        except FileNotFoundError:
            print(f"文件 '{local_file}' 未找到。")
        except NoCredentialsError:
            print("AWS 凭证未找到。")
        except ClientError as e:
            print(f"上传文件时发生错误：{e}")

    def _ensure_bucket(self):
        """
        检查 Bucket 是否存在，如果不存在则创建。
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            print(f"Bucket '{self.bucket_name}' 已存在。")
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                self.s3_client.create_bucket(
                    Bucket=self.bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.region}
                )
                print(f"Bucket '{self.bucket_name}' 创建成功。")
            else:
                print(f"检查或创建 Bucket 时发生错误：{e}")
                raise

    def get_presigned_url(self, object_name: str, expiration: int = 604800) -> str:
        """
        获取对象的预签名 URL。

        :param object_name: 对象名称
        :param expiration: URL 的有效期（秒），默认 7 天
        :return: 预签名 URL
        """
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_name},
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            print(f"生成预签名 URL 时发生错误：{e}")
            raise

    def download_file(self, object_name: str, local_file: str) -> None:
        """
        从 Bucket 中下载对象到本地文件。

        :param object_name: 对象名称
        :param local_file: 本地文件路径
        """
        try:
            self.s3_client.download_file(self.bucket_name, object_name, local_file)
            print(f"对象 '{object_name}' 已下载到本地文件 '{local_file}'。")
        except ClientError as e:
            print(f"下载对象时发生错误：{e}")
            raise

    def delete_file(self, object_name: str) -> None:
        """
        删除 Bucket 中的对象。

        :param object_name: 对象名称
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_name)
            print(f"对象 '{object_name}' 已从 Bucket '{self.bucket_name}' 中删除。")
        except ClientError as e:
            print(f"删除对象时发生错误：{e}")
            raise

    def list_objects(self, prefix: str = '') -> List[str]:
        """
        列出 Bucket 中的对象。

        :param prefix: 对象名称前缀，用于过滤
        :return: 对象名称列表
        """
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents']]
            else:
                return []
        except ClientError as e:
            print(f"列出对象时发生错误：{e}")
            raise

    def set_bucket_policy_public_read(self) -> None:
        """
        设置 Bucket 的策略为公共读取。
        """
        try:
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"]
                    }
                ]
            }
            policy_json = json.dumps(policy)
            self.s3_client.put_bucket_policy(Bucket=self.bucket_name, Policy=policy_json)
            print(f"Bucket '{self.bucket_name}' 的访问策略已设置为公共读取。")
        except ClientError as e:
            print(f"设置 Bucket 策略时发生错误：{e}")
            raise

    def remove_bucket_policy(self) -> None:
        """
        移除 Bucket 的策略。
        """
        try:
            self.s3_client.delete_bucket_policy(Bucket=self.bucket_name)
            print(f"Bucket '{self.bucket_name}' 的策略已移除。")
        except ClientError as e:
            print(f"移除 Bucket 策略时发生错误：{e}")
            raise

    def get_direct_url(self, object_name, expires_in=3600):
        """
        获取对象的直接访问链接。

        :param object_name: 对象名称
        :param expires_in: 预签名 URL 的有效期（秒），默认 3600 秒（1 小时）
        :return: 对象的直接访问链接
        """
        try:
            # 检查存储桶的公共访问权限
            bucket_policy = self.s3_client.get_bucket_policy(Bucket=self.bucket_name)
            if '"Effect":"Allow","Principal":"*","Action":"s3:GetObject"' in bucket_policy['Policy']:
                # 存储桶是公共读取的，直接构造 URL
                url = f"https://{self.bucket_name}.s3.amazonaws.com/{object_name}"
            else:
                # 存储桶不是公共读取的，生成预签名 URL
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': object_name},
                    ExpiresIn=expires_in
                )
            return url
        except ClientError as e:
            print(f"获取对象 URL 时发生错误：{e}")
            return None


def main():
    # 确保环境变量已设置
    os.environ['AWS_ACCESS_KEY_ID'] = 'YOUR_ACCESS_KEY_ID'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'YOUR_SECRET_ACCESS_KEY'
    os.environ['AWS_BUCKET_NAME'] = 'your-bucket-name'
    os.environ['AWS_REGION'] = 'us-east-1'

    # 初始化 S3Client，不需要传递参数，因为它会从环境变量中读取
    s3_client = S3Client()

    # 上传文件
    local_file = 'path/to/your/image.jpg'
    object_name = 'image.jpg'  # 或者使用 None 以自动获取文件名
    s3_client.upload_file(local_file, object_name)

    # 获取预签名 URL（有效期 7 天）
#     url = s3_client.get_presigned_url(object_name, expiration=604
# ::contentReference[oaicite:0]{index=0}
 
