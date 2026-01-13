try:
    from storages.backends.s3boto3 import S3Boto3Storage  # pyright: ignore[reportMissingImports]
except ImportError:
    # Fallback if storages is not installed
    S3Boto3Storage = None

#class StaticStorage(S3Boto3Storage):
#location = 'static'
#file_overwrite = True
#default_acl = 'public-read' # Set appropriate ACL for static files

if S3Boto3Storage:
    class MediaStorage(S3Boto3Storage):
        location = 'media'
        file_overwrite = False # Ensure media files with the same name are not overwritten
        default_acl = 'private' # Media files are typically private
else:
    # Fallback to FileSystemStorage if S3Boto3Storage is not available
    from django.core.files.storage import FileSystemStorage
    class MediaStorage(FileSystemStorage):
        location = 'media'