from urllib.parse import urlparse

from rest_framework import serializers


def external_resources(url):
    host = (urlparse(url).hostname or "").rstrip(".")
    is_youtube = host == "youtube.com" or host.endswith(".youtube.com")
    if not is_youtube:
        raise serializers.ValidationError("Запрещенный ресурс")
