import os
import json
import datetime
from minio import Minio
from minio.error import S3Error
from typing import List, Optional, Dict

class S3Client:
    """
    S3Client封装了与MinIO兼容的对象存储服务的常用操作。
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        region: str = 'us-east-1',
        secure: bool = False
    ):
        """
        初始化S3Client，支持通过环境变量配置。

        环境变量：
            MINIO_ENDPOINT
            MINIO_ACCESS_KEY
            MINIO_SECRET_KEY
            MINIO_BUCKET
            MINIO_REGION
            MINIO_SECURE
        """
        self.endpoint = endpoint or os.getenv('MINIO_ENDPOINT', '20.187.52.241:9000')
        self.access_key = access_key or os.getenv('MINIO_ACCESS_KEY', 'IgsRutWhylZ8R2pUR3e8')
        self.secret_key = secret_key or os.getenv('MINIO_SECRET_KEY', 'HpW0kcFUjE37lzw2YXaX2g7UVSHCRkbLBQWVq8py')
        self.bucket_name = bucket_name or os.getenv('MINIO_BUCKET', 'mini')
        # self.region = region or os.getenv('MINIO_REGION', 'us-east-1')
        self.secure = secure or (os.getenv('MINIO_SECURE', 'False').lower() == 'true')

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )

        self._ensure_bucket()

    def _ensure_bucket(self):
        """
        检查Bucket是否存在，如果不存在则创建。
        """
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name, location=self.region)
                print(f"Bucket '{self.bucket_name}' 创建成功。")
            else:
                print(f"Bucket '{self.bucket_name}' 已存在。")
        except S3Error as e:
            print(f"检查或创建Bucket时发生错误：{e}")
            raise

    def upload_file(self, local_file: str, object_name: Optional[str] = None) -> None:
        """
        上传文件到Bucket。

        :param local_file: 本地文件路径
        :param object_name: 上传后的对象名称，如果为None，则使用本地文件名
        """
        if object_name is None:
            object_name = os.path.basename(local_file)
        try:
            self.client.fput_object(self.bucket_name, object_name, local_file)
            print(f"文件 '{local_file}' 成功上传到Bucket '{self.bucket_name}' 作为对象 '{object_name}'。")
        except S3Error as e:
            print(f"上传文件时发生错误：{e}")
            raise
    def upload_stream(self, stream, object_name: Optional[str] = None,length=-1, part_size =10*1024*1024,  content_type = None) -> None:
        """
        上传流到Bucket。
        :param stream: 二进制流
        :param object_name: 上传后的对象名称
        :param metadata: 元数据
        """
        try:
            self.client.put_object(
                self.bucket_name,
                object_name,
                stream,
                length=length,
                part_size=part_size,
                content_type=content_type
            )
            print(f"流成功上传到Bucket '{self.bucket_name}' 作为对象 '{object_name}'。")
        except S3Error as e:
            print(f"上传流时发生错误：{e}")





    def upload_files(self, local_files: List[str], object_names: Optional[List[str]] = None) -> None:
        """
        批量上传文件到Bucket。

        :param local_files: 本地文件路径列表
        :param object_names: 上传后的对象名称列表。如果为None，则使用本地文件名
        """
        if object_names and len(local_files) != len(object_names):
            raise ValueError("local_files 和 object_names 的长度必须相同。")

        try:
            for idx, local_file in enumerate(local_files):
                object_name = object_names[idx] if object_names else os.path.basename(local_file)
                self.client.fput_object(self.bucket_name, object_name, local_file)
                print(f"文件 '{local_file}' 成功上传到Bucket '{self.bucket_name}' 作为对象 '{object_name}'。")
        except S3Error as e:
            print(f"批量上传文件时发生错误：{e}")
            raise

    def get_direct_url(self, object_name: str, days: int = 7) -> str:
        """
        获取对象的直接链接。

        :param object_name: 对象名称
        :param days: 链接的有效天数。若为-1，则返回公开URL（需Bucket或对象设置为公共读取）
        :return: 直接链接URL
        """
        try:
            if days == -1:
                # 构造公开URL
                url = f"http{'s' if self.secure else ''}://{self.endpoint}/{self.bucket_name}/{object_name}"
                return url
            else:
                # 生成预签名URL
                expires = datetime.timedelta(days=days)
                presigned_url = self.client.get_presigned_url(
                    "GET",
                    self.bucket_name,
                    object_name,
                    expires=expires
                )
                return presigned_url
        except S3Error as e:
            print(f"生成直接链接时发生错误：{e}")
            raise

    def download_file(self, object_name: str, local_file: str) -> None:
        """
        从Bucket中下载对象到本地文件。

        :param object_name: 对象名称
        :param local_file: 本地文件路径
        """
        try:
            self.client.fget_object(self.bucket_name, object_name, local_file)
            print(f"对象 '{object_name}' 已下载到本地文件 '{local_file}'。")
        except S3Error as e:
            print(f"下载对象时发生错误：{e}")
            raise

    def delete_file(self, object_name: str) -> None:
        """
        删除Bucket中的对象。

        :param object_name: 对象名称
        """
        try:
            self.client.remove_object(self.bucket_name, object_name)
            print(f"对象 '{object_name}' 已从Bucket '{self.bucket_name}' 中删除。")
        except S3Error as e:
            print(f"删除对象时发生错误：{e}")
            raise

    def list_objects(self, prefix: str = '') -> List[str]:
        """
        列出Bucket中的对象。

        :param prefix: 对象名称前缀，用于过滤
        :return: 对象名称列表
        """
        try:
            objects = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True)
            object_names = [obj.object_name for obj in objects]
            return object_names
        except S3Error as e:
            print(f"列出对象时发生错误：{e}")
            raise
  
    def set_bucket_policy_public_read(self) -> None:
        """
        设置Bucket的策略为公共读取。
        """
        try:
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": ["*"]},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"]
                    }
                ]
            }
            policy_json = json.dumps(policy)
            self.client.set_bucket_policy(self.bucket_name, policy_json)
            print(f"Bucket '{self.bucket_name}' 的访问策略已设置为公共读取。")
        except S3Error as e:
            print(f"设置Bucket策略时发生错误：{e}")
            raise

    def remove_bucket_policy_public_read(self) -> None:
        """
        移除Bucket的公共读取策略。
        """
        try:
            self.client.remove_bucket_policy(self.bucket_name)
            print(f"Bucket '{self.bucket_name}' 的公共读取策略已移除。")
        except S3Error as e:
            print(f"移除Bucket策略时发生错误：{e}")
            raise












def main():
    # 确保环境变量已设置
    os.environ['MINIO_ENDPOINT'] = "20.187.52.241:9000"
    os.environ['MINIO_ACCESS_KEY'] = 'IgsRutWhylZ8R2pUR3e8'
    os.environ['MINIO_SECRET_KEY'] = 'HpW0kcFUjE37lzw2YXaX2g7UVSHCRkbLBQWVq8py'
    os.environ['MINIO_BUCKET'] = 'pub-bucket'
    os.environ['MINIO_REGION'] = 'us-east-1'
    os.environ['MINIO_SECURE'] = 'False'

    # 初始化S3Client，不需要传递参数，因为它会从环境变量中读取
    s3_client = S3Client()

    # 上传文件
    local_file = 'D:/Data/Cheque/1.png'
    object_name = '1.png'  # 或者使用None以自动获取文件名
    s3_client.upload_file(local_file, object_name)

    # 获取预签名URL（有效期7天）
    url = s3_client.get_direct_url(object_name, days=7)
    print(f"预签名URL（有效期7天）：\n{url}")

    # 获取公开URL（需要设置Bucket为公共读取）
    # 首先设置Bucket策略为公共读取
    s3_client.set_bucket_policy_public_read()
    public_url = s3_client.get_direct_url(object_name, days=-1)
    print(f"公开URL：\n{public_url}")

    # 列出Bucket中的所有对象
    objects = s3_client.list_objects()
    print("Bucket中的对象：")
    for obj in objects:
        print(obj)
