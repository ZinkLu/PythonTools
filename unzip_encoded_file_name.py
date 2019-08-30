def unzip_encoded_file_name(src, tar, coding='utf-8'):
    """
    解决无法解压缩内部文件名为非utf8编码的zip包
    比如阿里的账单, zip中的文件名是用gbk编码的, 在mac下无法解压, 在linux下乱码
    :param src: zipfile的绝对路径
    :param tar: 需要解压的文件夹路径
    :param coding: 内部文件名编码方式
    :return: list 解压出来的文件名列表(使用指定的方式解码的字节)
    """
    file_list = list()
    with zipfile.ZipFile(src, 'r') as zf:
        for unzip_file in zf.filelist:
            decoded_file_name = unzip_file.filename.decode(coding)
            file_list.append(decoded_file_name)
            with zf.open(unzip_file) as tmp_zf:
                with open(os.path.join(tar, decoded_file_name), 'wb') as writer:
                    while True:
                        zip_content = tmp_zf.read(102400)  # 每次读取102400字节(100M)
                        if not zip_content:
                            break
                        writer.write(zip_content)
    return file_list
