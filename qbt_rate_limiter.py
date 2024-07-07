import requests
import xml.etree.ElementTree as ET
from qbittorrentapi import Client
import logging
from time import sleep
from dotenv import load_dotenv
from os import environ

load_dotenv()

def setup_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler('log.log')
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

logger = setup_logger()

def get_plex_sessions(plex_token):
    endpoint = f'http://localhost:32400/status/sessions?X-Plex-Token={plex_token}'
    try:
        response = requests.get(endpoint)
        response.raise_for_status()
        return ET.fromstring(response.content)
    except requests.RequestException as e:
        logger.error(f"Failed to retrieve sessions from Plex API: {e}")
        return None

def mbps_to_bps(mbps):
    try:
        bps = int(float(mbps) * 1024 * 1024)
        return bps if bps > 0 else -1
    except ValueError:
        logger.error("Invalid limit value provided.")
        return -1

def set_qbt_limits(client, upload_limit, download_limit):
    try:
        client.transfer_set_upload_limit(upload_limit)
        client.transfer_set_download_limit(download_limit)
        if upload_limit != -1:
            logger.info("Upload speed limit set in qBittorrent.")
        else:
            logger.info("Removed upload speed limit in qBittorrent.")
        
        if download_limit != -1:
            logger.info("Download speed limit set in qBittorrent.")
        else:
            logger.info("Removed download speed limit in qBittorrent.")
    except Exception as e:
        logger.error(f"Failed to set speed limits in qBittorrent: {e}")

def process_plex_sessions(root, client, upload_limit, download_limit):
    size = root.attrib.get('size', '0')
    if size != "0":
        logger.info("Someone is streaming from Plex!")
        sessions = root.findall('./Video')
        for session in sessions:
            attributes = session.attrib
            user = session.find('./User').attrib['title']
            library = attributes.get('librarySectionTitle')
            grandparent_title = attributes.get('grandparentTitle')
            parent_title = attributes.get('parentTitle')
            title = attributes.get('title')

            if grandparent_title:
                logger.info(f"User: {user}, Library: {library}, Title: {grandparent_title} - {parent_title} - {title}")
            else:
                logger.info(f"User: {user}, Library: {library}, Title: {title}")
        set_qbt_limits(client, upload_limit, download_limit)
    else:
        logger.info("No one is currently streaming from Plex.")
        set_qbt_limits(client, -1, -1)

def main():
    plex_token = environ.get("PLEX_TOKEN")
    qbt_host = environ.get("QBT_HOST")
    qbt_user = environ.get("QBT_USER")
    qbt_pass = environ.get("QBT_PASS")
    upload_limit_mbps = environ.get("UPLOAD_LIMIT_MBPS", "0")
    download_limit_mbps = environ.get("DOWNLOAD_LIMIT_MBPS", "0")

    if not all([plex_token, qbt_host, qbt_user, qbt_pass]):
        logger.error("One or more environment variables are missing.")
        return

    client = Client(host=qbt_host, username=qbt_user, password=qbt_pass)
    upload_limit = mbps_to_bps(upload_limit_mbps)
    download_limit = mbps_to_bps(download_limit_mbps)

    while True:
        root = get_plex_sessions(plex_token)
        if root:
            process_plex_sessions(root, client, upload_limit, download_limit)
        sleep(30)

if __name__ == "__main__":
    main()

