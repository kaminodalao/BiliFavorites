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
    all_video_list = []
    old_video_list = []

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
                self.new_video_list.append(video)
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

    def delete_unstar_video(self):
        query = database.session.query(database.VideoList.bvid).all()
        self.all_video_list = [item.bvid for item in query]
        new_video_list = [item["bvid"] for item in self.new_video_list]

        for v in self.all_video_list:
            if v not in new_video_list:
                for qv in (
                    database.session.query(database.VideoList).filter_by(bvid=v).all()
                ):
                    print("删除视频 %s(%s)" % (qv.bvid, qv.title))
                    database.session.query(database.VideoList).filter_by(
                        id=qv.id
                    ).delete()
                    database.session.commit()

    def write_row_to_video_docs(self, text=""):
        print(text)
        with open("docs/Video.md", "a", encoding="utf8") as f:
            f.write("%s\n" % text)

    def build_video_docs(self):
        print("生成Video.md文件")
        if os.path.exists("docs/Video.md"):
            os.unlink("docs/Video.md")
        self.write_row_to_video_docs("# VIDEO")
        self.write_row_to_video_docs(
            "build at %s  " % time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        )
        self.write_row_to_video_docs()
        self.write_row_to_video_docs("## INDEX")
        categories = database.session.query(database.VideoCategory).all()
        details_tmp = []
        for category in categories:
            self.write_row_to_video_docs("### %s" % category.title)
            videos = (
                database.session.query(database.VideoList)
                .filter_by(category=category.id)
                .all()
            )
            self.write_row_to_video_docs("| TITLE | BVID | UPNAME | STATUS |")
            self.write_row_to_video_docs("| ---- | ---- | ---- | ---- |")

            for video in videos:
                if video.status is not None:
                    status = video.status
                else:
                    status = ""
                self.write_row_to_video_docs(
                    "| [%s](#%s) | %s | %s | %s |"
                    % (
                        video.title.replace("|", "\|")
                        .replace("[", "\[")
                        .replace("]", "\]"),
                        video.bvid.lower(),
                        video.bvid,
                        video.upname,
                        status,
                    )
                )
                details_tmp.append("### %s" % video.bvid)

                qi = (
                    database.session.query(database.Assets)
                    .filter_by(source=video.cover)
                    .first()
                )
                if qi and qi.backup is not None:
                    cover = qi.backup
                else:
                    cover = ""
                """details_tmp.append(
                    f'<div align="center"><img alt="{video.title}" src="{cover}" width="50%" /></div>  '
                )"""
                details_tmp.append("![%s](%s)  " % (video.title, cover))
                details_tmp.append("Title: %s  " % video.title)
                details_tmp.append("Intro: %s  " % video.intro)
                details_tmp.append("Category: %s  " % category.title)
                details_tmp.append(
                    "Url: [https://www.bilibili.com/video/%s](https://www.bilibili.com/video/%s)  "
                    % (video.bvid, video.bvid)
                )
                details_tmp.append(
                    "UP: [%s](https://space.bilibili.com/%s)\[%s\]   "
                    % (video.upname, video.upid, video.upid)
                )

                details_tmp.append("")

        self.write_row_to_video_docs()
        self.write_row_to_video_docs("## DETAIL")

        for detail in details_tmp:
            self.write_row_to_video_docs(detail)
        print("完成")

    def start(self):
        self.update_video_list()
        self.delete_unstar_video()
        self.update_video_cover()
        self.build_video_docs()


if __name__ == "__main__":
    UID = os.getenv("UID")
    IMAGE_SERVER_API = os.getenv("IMAGE_SERVER_API")
    IMAGE_SERVER_KEY = os.getenv("IMAGE_SERVER_KEY")
    u = UpdateVideoStarList(UID, IMAGE_SERVER_API, IMAGE_SERVER_KEY)
    u.start()
