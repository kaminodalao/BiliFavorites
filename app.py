import base64
import datetime
import json
import os
import time
import re
import msal
import requests
from bilibili_api import favorite_list, sync, video
import logging

exit()


from office365.graph_client import GraphClient

logging.basicConfig(level=logging.INFO,
                    format="[%(levelname)s] [%(asctime)s] %(message)s",
                    datefmt='%Y-%m-%d %H:%M:%S'
                    )


class OnedrivePan:
    def __init__(self, tenant_id, client_id, client_secret, user_email, root_path=""):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_email = user_email
        self.root_path = root_path

        self.client = GraphClient(self.__acquire_token)

    def __acquire_token(self):
        authority_url = f'https://login.microsoftonline.com/{self.tenant_id}'
        app = msal.ConfidentialClientApplication(
            authority=authority_url,
            client_id=f'{self.client_id}',
            client_credential=f'{self.client_secret}'
        )
        token = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"])

        return token

    def __print_progress(self, range_pos):
        if self.local_file_length - range_pos <= 1000000:
            print("Uploaded ".format(
                  self.local_file_name))
        else:
            print("Uploading {1}%".format(round(
                  range_pos/self.local_file_length*100, 2)), end="\r")

    def get_remote_file_item(self, path):
        return self.client.users[self.user_email].drive.root.get_by_path(
            "%s%s" % (self.root_path, path))

    def upload_file(self, local_path, remote_dir):
        with open(local_path, "rb") as f:
            self.local_file_length = len(f.read())
        self.local_file_name = local_path.split("/")[-1]
        file_item = self.get_remote_file_item(remote_dir).resumable_upload(
            local_path, chunk_uploaded=self.__print_progress).execute_query()

        return file_item.web_url


class Video:
    def __init__(self, init={}):
        self.data = init

    def set_bvid(self, bvid):
        self.data["bvid"] = bvid

        return self

    @property
    def bvid(self):
        return self.data["bvid"]

    def set_title(self, title):
        self.data["title"] = title

        return self

    @property
    def title(self):
        return self.data["title"]

    def set_description(self, desc):
        self.data["description"] = desc

        return self

    @property
    def description(self):
        return self.data["description"]

    def set_cover(self, cover_url):
        self.data["cover"] = cover_url

        return self

    @property
    def cover(self):
        return self.data["cover"]

    def set_cover_backup(self, cover_backup_url):
        self.data["cover_backup"] = cover_backup_url

        return self

    @property
    def cover_backup(self):
        return self.data["cover_backup"]

    def set_category_id(self, cid):
        self.data["category_id"] = cid

        return self

    @property
    def category_id(self):
        return self.data["category_id"]

    def set_category_name(self, cname):
        self.data["category_name"] = cname

        return self

    @property
    def category_name(self):
        return self.data["category_name"]

    def set_up_id(self, upid):
        self.data["up_id"] = upid

        return self

    @property
    def up_id(self):
        return self.data["up_id"]

    def set_up_name(self, up_name):
        self.data['up_name'] = up_name

        return self

    @property
    def up_name(self):
        return self.data['up_name']

    def set_up_face(self, up_face):
        self.data["up_face"] = up_face

        return self

    @property
    def up_face(self):
        return self.data["up_face"]

    def set_status(self, status):
        self.data["status"] = status

        return self

    @property
    def status(self):
        return self.data["status"]

    def set_publish(self, publish):
        self.data["publish"] = publish

        return self

    @property
    def publish(self):
        return self.data["publish"]

    def update(self, data={}):
        updated = False
        for k, v in data.items():
            if self.data[k] != v:
                self.data[k] = v
                updated = True
        if updated:
            self.data["update"] = int(time.time())

        return self.data

    def to_array(self):
        return self.data


class Videos:
    def __init__(self):
        self.video_save_file = os.path.abspath("database/videos.json")
        if not os.path.exists(self.video_save_file):
            with open(self.video_save_file, "w") as f:
                f.write(json.dumps({}))
        with open(self.video_save_file) as fr:
            self.videos = json.loads(fr.read())

            print("Read %s video record from %s" %
                  (len(self.videos), self.video_save_file))

    def video_exists(self, bvid):
        return bvid in self.videos.keys()

    def get_video(self, bvid):
        if bvid in self.videos.keys():
            return Video(self.videos[bvid])
        else:
            raise Exception("Not Found Video %s" % bvid)

    def update_database(self):
        with open(self.video_save_file, "w") as f:
            f.write(json.dumps(self.videos))

    def add_video(self, video):
        self.videos[video.bvid] = video.to_array()


class BiliFavorites:

    def __init__(self, uid, onedrive_config):
        self.uid = uid
        self.video_save_file = os.path.abspath("database/videos.json")
        self.get_saved_favorities()
        self.od = OnedrivePan(os.getenv("ONEDRIVE_TENANT_ID"), os.getenv("ONEDRIVE_CLIENT_ID"), os.getenv(
            "ONEDRIVE_CLIENT_SECRET"), os.getenv("ONEDRIVE_USER_EMAIL"), os.getenv("ONEDRIVE_ROOT_PATH"))

    def get_saved_favorities(self):
        def _create_new_save_file():
            with open(self.video_save_file, "w") as f:
                f.write(json.dumps({}))
        if not os.path.exists(self.video_save_file):
            _create_new_save_file()
            logging.info("Create Save File")

        def _load_saved_file():
            with open(self.video_save_file) as fr:
                self.saved_favorities = json.loads(fr.read())
                self.saved_bvid = self.saved_favorities.keys()
                logging.info("Load Saved Video %s" %
                             len(self.saved_favorities))
        try:
            _load_saved_file()
        except Exception as e:
            logging.error(str(e))
            logging.info("delete saved file")
            os.unlink(self.video_save_file)
            _create_new_save_file()
            _load_saved_file()

    def get_current_favorities(self):
        data = {}
        for category in sync(favorite_list.get_video_favorite_list(self.uid))["list"]:
            logging.debug("Get Categorty %s", category['title'])
            page = 1
            while True:
                logging.info("Get Page %s" % page)
                query = sync(favorite_list.get_video_favorite_list_content(category['id'], page))[
                    "medias"
                ]
                if query is None:
                    logging.info("List Empty")
                    break
                for item in query:
                    _item = item
                    _item['category'] = category
                    _item['updated'] = int(time.time())

                    if _item['bvid'] not in self.saved_bvid:
                        logging.info("New Video %s" % _item['title'])
                        if _item['title'] == '已失效视频':
                            _item['status'] = 'LOST'
                        else:
                            _item['status'] = None
                            v = video.Video(bvid=_item['bvid'])
                            _item['info'] = sync(v.get_info())

                    data[_item['bvid']] = _item
                    logging.debug("Get Video %s" % item['title'])
                page += 1
        self.current_favorities = data

        self.save_data_file()

        return data

    def save_data_file(self):
        with open(self.video_save_file, "w") as f:
            f.write(json.dumps(self.current_favorities))

    def backup_cover_image(self):
        for bvid, video in self.current_favorities.items():
            if 'cover_backup' not in video or video['cover_backup'] is None:
                try:
                    logging.info("Backup Cover File %s" % video['cover'])
                    tempfile = os.path.abspath(
                        "download/%s" % video['cover'].split('/')[-1])
                    response = requests.get(video['cover'], timeout=5, headers={
                                            'user-agent': 'Mozilla/5.0 (X11; U; Linux i686; rv:1.7.8) Gecko/20060628 Debian/1.7.8-1sarge7.1'})
                    with open(tempfile, "wb") as f:
                        f.write(response.content)
                    remote_url = self.od.upload_file(
                        tempfile, '/Covers')
                    self.current_favorities[bvid]['cover_backup'] = remote_url
                    self.save_data_file()
                    os.unlink(tempfile)
                except Exception as e:
                    logging.error(str(e))


if __name__ == "__main__":
    r = BiliFavorites(os.getenv("BILIBILI_UID"), [])

    r.get_current_favorities()
    r.backup_cover_image()
