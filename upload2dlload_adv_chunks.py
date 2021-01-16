#!/usr/bin/python3
# upload file to dlload.com/disk
# using python3.5 requests-2.24.0 requests-toolbelt-0.9.1

import requests
import uuid
import os
import time
import sys
import itertools
import random
import filemapper
import hashlib
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

# 分片大小，不能太小且要符合对其要求，太小不符合mmap的offset约束
chunkSize = 1024 * 1024 * 5
uri = "https://dlload.com/disk"
#uri = "https://10.41.173.201:80"


def my_callback(monitor):
    progress = (monitor.bytes_read / monitor.len) * 100
    print("\r upload progress：%d%%(%d/%d)"
          % (progress, monitor.bytes_read, monitor.len), end=' ')


def get_boundary():
    rnd = random.Random(time.time())
    aa = itertools.starmap(rnd.randint, itertools.repeat((100, 999), 10))
    bb = map(str, aa)
    cc = ''.join(bb)
    return '-' * 27 + cc


# 分块传输
def chunks_transfer(file_path, file_obj, stat_info):
    guid = str(uuid.uuid4())
    file_name = os.path.basename(file_path)
    last_modified_date = time.strftime('%m/%d/%Y, %I:%M:%S %p', time.localtime(stat_info.st_mtime))
    file_size = str(stat_info.st_size)

    # 完整块数、剩余字节
    complete_chunks, remainder = divmod(stat_info.st_size, chunkSize)
    total_chunks = complete_chunks
    if remainder != 0:
        total_chunks += 1
    md5 = hashlib.new('md5')
    with requests.Session() as session:
        # 分块传输
        for index in range(complete_chunks):
            with filemapper.FileMMap(file_obj.fileno(),
                                     length=chunkSize,
                                     access=filemapper.ACCESS_READ,
                                     offset=index * chunkSize) as mm:
                # dlload.com的chunk从0开始
                post_chunk_data(session, file_name, mm, file_size, guid,
                                index, last_modified_date, total_chunks)
                md5.update(mm.reset().read())

        if remainder != 0:
            with filemapper.FileMMap(file_obj.fileno(),
                                     length=remainder,
                                     access=filemapper.ACCESS_READ,
                                     offset=complete_chunks * chunkSize) as mm:
                post_chunk_data(session, file_name, mm, file_size, guid,
                                complete_chunks, last_modified_date, total_chunks)
                md5.update(mm.reset().read())

        # 合并
        res = session.post(
            uri,
            headers={
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "en-US,en;q=0.5",
                'Content-Type': "application/x-www-form-urlencoded; charset=UTF-8",
                'X-Requested-With': 'XMLHttpRequest',
                "Host": "dlload.com",
                "Origin": "https://dlload.com",
                "Referer": "https://dlload.com/disk",
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:84.0) Gecko/20100101 Firefox/84.0"
            },
            data=[
                ('action', 'merge'),
                ('id', 'WU_FILE_0'),
                ('size', file_size),
                ('name', file_name),
                ('md5', md5.hexdigest()),
                ('token', ''),
                ('guid', guid),
            ]
        )
        print(res.content)


def post_chunk_data(session, file_name, file_data, file_size, guid, chunk_index, last_modified_date, total_chunks):
    print('upload chunk {}/{}'.format(chunk_index, total_chunks))
    chunk_field = [("chunks", str(total_chunks)),
                   ("chunk", str(chunk_index))
                   ]
    file_field = ('file', (file_name, file_data, 'application/octet-stream'))

    post_multipart_data(session, guid, file_name,
                        file_size, last_modified_date, file_field, chunk_field)


def post_multipart_data(session, guid, file_name, file_size, last_modified_date, file_field, chunk_field=[]):
    fields = [
        ("token", ""),
        ("guid", guid),
        ("id", "WU_FILE_0"),
        ("name", file_name),
        ("type", "application/zip",),
        ("lastModifiedDate", last_modified_date),
        ("size", file_size)
    ]
    fields.extend(chunk_field)
    fields.append(file_field)
    encoder = MultipartEncoder(fields=fields,
                               boundary=get_boundary())
    encoder = MultipartEncoderMonitor(encoder, my_callback)

    res = session.post(
        uri,
        headers={
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.5",
            'Content-Type': encoder.content_type,
            "Host": "dlload.com",
            "Origin": "https://dlload.com",
            "Referer": "https://dlload.com/disk",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:84.0) Gecko/20100101 Firefox/84.0"
        },
        data=encoder
    )
    print('\n', res.content)


# 一次性传输
def single_transfer(file_path, file_obj, stat_info):
    guid = str(uuid.uuid4())
    file_name = os.path.basename(file_path)
    file_size = str(stat_info.st_size)
    last_modified_date = time.strftime('%m/%d/%Y, %I:%M:%S %p', time.localtime(stat_info.st_mtime))
    file_field = ('file', (file_name, file_obj, 'application/zip'))

    with requests.Session() as session:
        post_multipart_data(session, guid, file_name,
                            file_size, last_modified_date, file_field)


def main():
    if len(sys.argv) >= 2:
        file_path = sys.argv[1]
        print('Going to upload {}'.format(file_path))
    else:
        print('Usage:')
        print('{} file_to_upload'.format(sys.argv[0]))
        sys.exit(-1)
    with open(file_path, "rb") as file_obj:
        stat_info = os.stat(file_path)
        if stat_info.st_size > chunkSize:
            chunks_transfer(file_path, file_obj, stat_info)
        else:
            single_transfer(file_path, file_obj, stat_info)


if __name__ == '__main__':
    # print(get_boundary())
    main()

