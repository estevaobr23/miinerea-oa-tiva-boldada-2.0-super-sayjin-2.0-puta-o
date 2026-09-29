from .meta import MetaProvider
from .tiktok import TikTokProvider
from .google import GoogleProvider

PROVIDER_CLASSES = {
    "meta": MetaProvider,
    "tiktok": TikTokProvider,
    "google": GoogleProvider,
}
