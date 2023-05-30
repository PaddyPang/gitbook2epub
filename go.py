import mkepub
import os
import re
import markdown
import shutil
import datetime
import random
import string
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()


def get_content(bookObj, base_dir, filename, default=""):

    if filename == "":
        return default

    filename = os.path.join(base_dir, filename)

    if os.path.exists(filename):
        print(f"File {filename} exists!")
        with open(filename, "r") as file:
            html = markdown.markdown(file.read())
            soup = BeautifulSoup(html, "html.parser")
            for img in soup.find_all("img"):
                imgName = img["src"].split('/')[1]
                with open(os.path.join(base_dir, img["src"]), 'rb') as file:
                    bookObj.add_image(imgName, file.read())
                img["src"] = "images/%s" % imgName
            return soup
    else:
        print(f"File {filename} does not exist!")
        return default


def make_epub_book(bookObj, guide_file, base_dir, bookFile):
    chapters = []
    with open(guide_file, 'r') as f:
        current_item = None

        for line in f:
            indent = len(line) - len(line.lstrip())
            if not line.strip().startswith('# ') and indent == 0:
                if current_item:
                    chapters.append(current_item)

                title = re.findall(
                    r'\[(.*?)\]', line)[0] if re.findall(r'\[(.*?)\]', line) else line.strip()
                if title.startswith('- '):
                    title = title[2:]

                link = re.findall(
                    r'\((.*?)\)', line)[0] if re.findall(r'\((.*?)\)', line) else ""

                current_item = {"title": title, "link": link, "son_items": []}
            elif indent == 2 and current_item:
                title = re.findall(r'\[(.*?)\]', line)[0]
                link = re.findall(r'\((.*?)\)', line)[0]
                info = {"title": title, "link": link}
                current_item["son_items"].append(info)

        if current_item:
            chapters.append(current_item)

    for chapter in chapters:
        title = chapter["title"]
        content = get_content(
            bookObj, base_dir, chapter["link"], chapter["title"])

        chapter_item = bookObj.add_page(title, content)
        if len(chapter['son_items']) > 0:
            for chapter_son in chapter['son_items']:
                title = chapter_son["title"]
                content = get_content(
                    bookObj, base_dir, chapter_son["link"], chapter_son["title"])
                bookObj.add_page(
                    title,
                    content,
                    parent=chapter_item
                )

    output_dir = os.path.join(base_dir, "out")
    os.makedirs(output_dir, exist_ok=True)

    if os.path.exists(bookFile):
        backup_and_rename_file(bookFile)

    print("out dir: %s" % output_dir)
    bookObj.save(bookFile)


def backup_and_rename_file(file_path):
    now = datetime.datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H-%M")
    random_number = ''.join(random.choices(string.digits, k=4))
    file_name, file_ext = os.path.splitext(file_path)
    backup_file_name = f"{file_name}_{current_date}_{current_time}_{random_number}{file_ext}"
    shutil.move(file_path, backup_file_name)
    print("backup_file_name:", backup_file_name)


def main():
    bookTitle = input("请输入书籍名称：")
    if not bookTitle:
        return False

    input_prompt = "请输入作者信息(默认: %s)：" % os.getenv('DEFAULT_AUTHORS')
    bookAuthors = input(input_prompt)
    if not bookAuthors:
        bookAuthors = os.getenv('DEFAULT_AUTHORS')

    default_dir = "books/%s/" % bookTitle
    base_dir = input("请输入书籍Makrdown目录(默认: %s)：" % default_dir)
    if not base_dir:
        base_dir = default_dir

    unsplash_params = {
        "client_id": os.getenv('UNSPLASH_CLIENT_ID'),
        "count":  1,
        "orientation": os.getenv('UNSPLASH_ORIENTATION'),
        "query": os.getenv('UNSPLASH_QUERY')
    }

    guide_file = os.path.join(base_dir, './SUMMARY.md')
    cover = os.path.join(base_dir, './res/images/cover.jpg')
    style = os.path.join(base_dir, './res/css/style.css')
    bookFile = os.path.join(base_dir, "out", bookTitle + '.epub')

    bookObj = mkepub.Book(title=bookTitle, author=bookAuthors)

    if not os.path.exists(cover):
        print("未查到封面, 等待下载新封面...")
        url = "https://api.unsplash.com/photos/random"
        response = requests.get(url, params=unsplash_params)
        if response.status_code == 200:
            images_info = response.json()
            response = requests.get(images_info[0]["urls"]['thumb'])
            if response.status_code == 200:
                with open(cover, "wb") as f:
                    f.write(response.content)
                print(f"图片已下载并保存到：{cover}")
            else:
                print("图片下载失败:", response.status_code)
        else:
            print("请求失败:", response.status_code)
    with open(cover, 'rb') as file:
        bookObj.set_cover(file.read())

    if os.path.exists(style):
        with open(style) as file:
            bookObj.set_stylesheet(file.read())
    make_epub_book(bookObj, guide_file, base_dir, bookFile)


if __name__ == "__main__":
    main()
