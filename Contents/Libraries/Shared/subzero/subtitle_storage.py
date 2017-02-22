# coding=utf-8
import datetime
import hashlib
import os

from constants import mode_map


class StoredSubtitle(object):
    score = None
    storage_type = None
    hash = None
    provider_name = None
    id = None
    date_added = None
    mode = "a"  # auto/manual/auto-better (a/m/b)
    content = None

    def __init__(self, score, storage_type, hash, provider_name, id, date_added=None, mode="a", content=None):
        self.score = int(score)
        self.storage_type = storage_type
        self.hash = hash
        self.provider_name = provider_name
        self.id = id
        self.date_added = date_added or datetime.datetime.now()
        self.mode = mode
        self.content = content

    @property
    def mode_verbose(self):
        return mode_map.get(self.mode, "Unknown")


class StoredVideoSubtitles(object):
    """
    manages stored subtitles for video_id per media_part/language combination
    """
    video_id = None  # rating_key
    title = None
    parts = None
    version = None

    def __init__(self, video_id, title, version=None):
        self.video_id = str(video_id)
        self.title = title
        self.parts = {}
        self.version = version

    def add(self, part_id, lang, subtitle, storage_type, date_added=None, mode="a"):
        part_id = str(part_id)
        part = self.parts.get(part_id)
        if not part:
            self.parts[part_id] = {}
            part = self.parts[part_id]

        subs = part.get(lang)
        if not subs:
            part[lang] = {}
            subs = part[lang]

        sub_key = self.get_sub_key(subtitle.provider_name, subtitle.id)
        if sub_key in subs:
            return

        subs[sub_key] = StoredSubtitle(subtitle.score, storage_type, hashlib.md5(subtitle.content).hexdigest(),
                                       subtitle.provider_name, subtitle.id, date_added=date_added, mode=mode,
                                       content=subtitle.content)
        subs["current"] = sub_key

        return True

    def get_any(self, part_id, lang):
        part_id = str(part_id)
        part = self.parts.get(part_id)
        if not part:
            return

        subs = part.get(lang)
        if not subs:
            return

        if "current" in subs and subs["current"]:
            return subs.get(subs["current"])

    def get_sub_key(self, provider_name, id):
        return provider_name, str(id)

    def __repr__(self):
        return unicode(self)

    def __unicode__(self):
        return u"%s (%s)" % (self.title, self.video_id)

    def __str__(self):
        return str(self.video_id)


class StoredSubtitlesManager(object):
    """
    manages the storage and retrieval of StoredVideoSubtitles instances for a given video_id
    """
    storage = None
    version = 1

    def __init__(self, storage):
        self.storage = storage

    def get_storage_filename(self, video_id):
        return "subs_%s" % video_id

    @property
    def dataitems_path(self):
        return os.path.join(getattr(self.storage, "_core").storage.data_path, "DataItems")

    def get_all_files(self):
        return os.listdir(self.dataitems_path)

    def get_recent_files(self, age_days=30):
        fl = []
        root = self.dataitems_path
        recent_dt = datetime.datetime.now() - datetime.timedelta(days=age_days)
        for fn in self.get_all_files():
            if not fn.startswith("subs_"):
                continue

            finfo = os.stat(os.path.join(root, fn))
            created = datetime.datetime.fromtimestamp(finfo.st_ctime)
            if created > recent_dt:
                fl.append(fn)
        return fl

    def load_recent_files(self, age_days=30):
        fl = self.get_recent_files(age_days=age_days)
        out = {}
        for fn in fl:
            out[fn] = self.storage.LoadObject(fn)
        return out

    def load(self, video_id):
        subs_for_video = self.storage.LoadObject(self.get_storage_filename(video_id))
        return subs_for_video

    def load_or_new(self, video_id, title):
        subs_for_video = self.load(video_id)
        if not subs_for_video:
            subs_for_video = StoredVideoSubtitles(video_id, title, version=self.version)
            self.save(subs_for_video)
        return subs_for_video

    def save(self, subs_for_video):
        self.storage.SaveObject(self.get_storage_filename(subs_for_video.video_id), subs_for_video)