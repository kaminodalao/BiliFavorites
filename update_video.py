from bilibili_api import sync, favorite_list
import json
import time
import pymysql
import database
import datetime
import requests
import base64
import os

class UpdateVideoStarList:

    new_video_list = []

    def __init__(self, uid, image_server_api, image_server_key):
        print("连接到数据库")
        database.init_db()
        self.uid = uid
        self.image_server_api = image_server_api
        self.image_server_key = image_server_key

    def get_video_categories(self):
        return sync(favorite_list.get_video_favorite_list(self.uid))["list"]

    def get_video_list_by_category_id(self, cid):
        data = []
        count = 0
        page = 1
        while True:
            query = sync(favorite_list.get_video_favorite_list_content(cid, page))[
                "medias"
            ]
            if query is None:
                break
            for item in query:
                data.append(item)
                count += 1
            page += 1

        return data

    def update_video_list(self):
        for category in self.get_video_categories():
            print("获取到视频分类 %s(%s) -> " % (category["id"], category["title"]), end="")
            qc = (
                database.session.query(database.VideoCategory)
                .filter_by(cid=category["id"])
                .first()
            )

            if not qc:
                qc = database.VideoCategory(cid=category["id"], title=category["title"])
                database.session.add(qc)
                database.session.commit()

                print("已添加到数据库")
            else:
                print("已存在该记录")

            category_id = qc.id

            for video in self.get_video_list_by_category_id(category["id"]):
                print("获取到视频 %s(%s) -> " % (video["bvid"], video["title"]), end="")
                qv = (
                    database.session.query(database.VideoList)
                    .filter_by(bvid=video["bvid"])
                    .first()
                )
                if not qv:
                    qv = database.VideoList(
                        category=category_id,
                        vid=video["id"],
                        bvid=video["bvid"],
                        title=pymysql.converters.escape_string(video["title"]),
                        intro=pymysql.converters.escape_string(video["intro"]),
                        cover=video["cover"],
                        upid=video["upper"]["mid"],
                        upname=pymysql.converters.escape_string(video["upper"]["name"]),
                        upface=video["upper"]["face"],
                        pubtime=datetime.datetime.fromtimestamp(video["pubtime"]),
                    )
                    if video["title"] == "已失效视频":
                        qv.status = "LOST"

                    database.session.add(qv)
                    database.session.commit()

                    self.new_video_list.append(qv.id)

                    print("已添加到数据库")
                else:
                    print("已存在该记录")

    def update_video_cover(self):
        cover_list = [
            c.cover for c in database.session.query(database.VideoList.cover).all()
        ]
        for cover in cover_list:
            query = ( 
                database.session.query(database.Assets).filter_by(source=cover).first()
            )
            if query and query.backup is not None:
                continue
            print("开始备份封面文件 %s" % cover)
            response = requests.get(
                cover,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36 Edg/97.0.1072.55"
                },
            )

            image_b64 = base64.b64encode(response.content)

            response = requests.post(
                self.image_server_api,
                data={
                    "key": self.image_server_key,
                    "format": "json",
                    "source": image_b64,
                },
            )
            data = json.loads(response.content.decode("utf8"))

            if data["status_code"] == 200:
                image_url = data["image"]["url"]
                print("上传到图床成功 %s" % image_url)
                asset = (
                    database.session.query(database.Assets)
                    .filter_by(source=cover)
                    .first()
                )
                if asset:
                    asset.backup = image_url
                    database.session.commit()
                else:
                    asset = database.Assets(
                        type="image", source=cover, backup=image_url
                    )
                    database.session.add(asset)
                    database.session.commit()
            else:
                print("上传图床失败 %s" % data["error"]["message"])

    def start(self):
        self.update_video_list()
        self.update_video_cover()


if __name__ == "__main__":
    UID = os.getenv("UID")
    IMAGE_SERVER_API = os.getenv("IMAGE_SERVER_API")
    IMAGE_SERVER_KEY = os.getenv("IMAGE_SERVER_KEY")
    u = UpdateVideoStarList(UID, IMAGE_SERVER_API, IMAGE_SERVER_KEY)
    u.start()
