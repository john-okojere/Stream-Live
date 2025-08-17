from storages.backends.s3boto3 import S3Boto3Storage


class StaticStorage(S3Boto3Storage):
    location = "dashboard/static"
    # default_acl = 'public-read'  ✅ COMMENT THIS OUT
    file_overwrite = True


class MediaStorage(S3Boto3Storage):
    location = "dashboard/media"
    file_overwrite = False
