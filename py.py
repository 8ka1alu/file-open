# -*- coding: utf-8 -*-
import discord
import datetime
import os
import sqlite3
from contextlib import closing
import chess.chess as chess # chessフォルダのchess.pyをimportする
import requests
import json

client = discord.Client()

@client.event
async def on_ready():
    print(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S - ") + client.user.name + "がログインしました")

# データベース名
dbname = "py.db"
# 言葉を覚えさせる時に使うフラグ
DBFlag = 0
# 言葉を覚えさせるユーザー
keywordAuthor = ""
# 覚える言葉を一時的に保存する文字列
keywordMemory = ""

# python実行時のOSを判断する
cmdPython = ""
if os.name == 'nt':
    cmdPython = "python"
elif os.name == 'posix':
    cmdPython = "python3"

chessplaying = False
chessboard = ''

@client.event
async def on_message(message):

    global DBFlag
    global keywordMemory
    global dbname
    global keywordAuthor
    global cmdPython
    global chessplaying
    global chessboard

    if message.author == client.user:
        return

    #ボットの相手はしない
    if message.author.bot:
        return

    if "白上フブキ" in message.content:
        url = "https://www.googleapis.com/youtube/v3/search?key=AIzaSyBoAhG9tKflz-4za3vjEmdRBsJEVGbd1Xw&channelId=UCdn5BQ06XqgXoAxIhbqw5Rg&part=snippet&eventType=upcoming&type=video"
        r = requests.get(url)

        data = ''
        if r.status_code == 200:
            data = json.loads(r.content)

        videoIds = []
        for key in data['items']:
            videoIds.append(key['id']['videoId'])

        url = "https://www.googleapis.com/youtube/v3/videos?key=AIzaSyBoAhG9tKflz-4za3vjEmdRBsJEVGbd1Xw&part=snippet,liveStreamingDetails&id="

        result_str = '「白上フブキ」さんのライブストリームの予定は以下の通りです。\n\n'

        for videoId in videoIds:
            r = requests.get(url + videoId)
            if r.status_code == 200:
                data = json.loads(r.content)
            tstr = data['items'][0]['liveStreamingDetails']['scheduledStartTime']
            tstr = tstr.replace('Z', '')
            tdatetime = datetime.datetime.fromisoformat(tstr).strftime("%Y/%m/%d %H:%M:%S")
            result_str = result_str + "時間：" + str(tdatetime) + "\n"
            result_str = result_str + "タイトル：" + data['items'][0]['snippet']['title'] + "\n"
            result_str = result_str + "URL：" + "https://www.youtube.com/watch?v=" + videoId + "\n\n"
        await message.channel.send(result_str)

    if "履歴検索" in message.content:
        resultstr = ""
        members = message.guild.members
        async for searchuser in message.channel.history(limit=1000):
            for i in range(len(members)):
                if searchuser.author.name == members[i].name:
                    if members[i].bot:
                        members.pop(i)
                        break
                    resultstr = resultstr + members[i].name + ":" + (searchuser.created_at + datetime.timedelta(hours=9)).strftime("%Y/%m/%d %H:%M:%S : ") + searchuser.content + "\n\n"
                    members.pop(i)
                    break
        await message.channel.send(resultstr)

    if "pyちゃんおやすみ" in message.content:
        await message.channel.send("寝ます。おやすみなさい。")
        await client.logout()

    if "チェス開始" in message.content:
        if chessplaying:
            return
        chessboard = chess.Chessboard()
        await message.channel.send(file=discord.File(chessboard.imagepath))
        await message.channel.send("チェスを開始します\n" + chessboard.color + "の番です。")

        chessplaying = True

    if "チェス終了" in message.content:
        if not chessplaying:
            return
        await message.channel.send("チェスを終了します")
        chessplaying = False

    # チェスプレイ中
    if chessplaying:
        if chessboard.promotion_flag == 2:
            if "クイーン" in message.content:
                chessboard.promotion("クイーン")
                chessboard.draw()
                await message.channel.send(file=discord.File(chessboard.imagepath))
                await message.channel.send("ポーンをクイーンに昇格しました。")
                chessboard.promotion_flag = 0
            elif "ビショップ" in message.content:
                chessboard.promotion("ビショップ")
                chessboard.draw()
                await message.channel.send(file=discord.File(chessboard.imagepath))
                await message.channel.send("ポーンをビショップに昇格しました。")
                chessboard.promotion_flag = 0
            elif "ナイト" in message.content:
                chessboard.promotion("ナイト")
                chessboard.draw()
                await message.channel.send(file=discord.File(chessboard.imagepath))
                await message.channel.send("ポーンをナイトに昇格しました。")
                chessboard.promotion_flag = 0
            elif "ルーク" in message.content:
                chessboard.promotion("ルーク")
                chessboard.draw()
                await message.channel.send(file=discord.File(chessboard.imagepath))
                await message.channel.send("ポーンをルークに昇格しました。")
                chessboard.promotion_flag = 0

        if chessboard.input_check(message.content):
            resultbool, resultstr = chessboard.progress(message.content)
            if resultbool:
                await message.channel.send(file=discord.File(chessboard.imagepath))
            await message.channel.send(resultstr)
            if chessboard.promotion_flag == 1:
                await message.channel.send("\nポーンを昇格させてください。\n 「クイーン」「ビショップ」「ナイト」「ルーク」どれにしますか？")
                chessboard.promotion_flag = 2

    # 覚える・忘れるをキャンセル
    if "やっぱりいいや" in message.content:
        DBFlag = 0
        keywordAuthor = ""
        await message.channel.send("そ、そうですかわかりました・・・")
        return

    # 覚える時
    if DBFlag == 2 and (message.author == keywordAuthor):
        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()
            create_table = "CREATE TABLE IF NOT EXISTS keywords(keyword, response, username, deleteflag)"
            c.execute(create_table)

            sql = "insert into keywords (keyword, response, username, deleteflag) values (?,?,?,?)"
            words = (keywordMemory , message.content, str(message.author), 0)
            c.execute(sql, words)
            conn.commit()

        await message.channel.send("お、覚えました・・・")
        DBFlag = 0
        keywordAuthor = ""
        return

    if (DBFlag == 1) and (message.author == keywordAuthor) :
        await message.channel.send("なんて返事したらいいでしょうか・・・？")
        keywordMemory = message.content
        DBFlag = 2
        return

    if "pyちゃん覚えて" in message.content:
        if DBFlag == 0:
            await message.channel.send("何を覚えたらいいでしょうか・・・？")
            DBFlag = 1
            keywordAuthor = message.author
            return

    # 忘れる時
    if DBFlag == 4 and (message.author == keywordAuthor):
        if message.content == "はい":
            with closing(sqlite3.connect(dbname)) as conn:
                c = conn.cursor()
                create_table = "CREATE TABLE IF NOT EXISTS keywords(keyword, response, username, deleteflag)"
                c.execute(create_table)

                sql = "update keywords set deleteflag = 1 where keyword = ?"
                words = (keywordMemory ,)
                c.execute(sql, words)
                conn.commit()

            await message.channel.send("忘れました")
            DBFlag = 0
            keywordAuthor = ""
            return

        elif message.content == "いいえ":
            await message.channel.send("やっぱりやめておきますか？そうですか・・・")
            DBFlag = 0
            keywordAuthor = ""
            return

        else:
            await message.channel.send("「はい」か「いいえ」で答えてほしいです")
            return

    if (DBFlag == 3) and (message.author == keywordAuthor) :
        sql = ""
        word = ()
        if (str(message.author) == "みり#9703"):
            sql = "select keyword, response from keywords where ? = keyword and deleteflag=0"
            word = (message.content,)
        else:
            sql = "select keyword, response, username from keywords where ? = keyword and deleteflag=0 and username = ?"
            word = (message.content, str(message.author))

        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()
            create_table = "CREATE TABLE IF NOT EXISTS keywords(keyword, response, username, deleteflag)"
            c.execute(create_table)
            find_flag = 0
            for row in c.execute(sql, word):
                if row[0] != "":
                    find_flag = 1
                    await message.channel.send("キーワード：" + row[0] + " / レスポンス：" + row[1])
            if find_flag == 0:
                await message.channel.send("キーワードが見つからないです　キーワードを変更するか「やっぱりいいや」でキャンセルしてほしいです")
                return
            await message.channel.send("本当にこれを忘れますか？　はい　いいえ")
        keywordMemory = message.content
        DBFlag = 4
        return

    if "pyちゃん忘れて" in message.content:
        if DBFlag == 0:
            await message.channel.send("何を忘れたらいいでしょうか・・・？")
            DBFlag = 3
            keywordAuthor = message.author
            return

    # データベース内を検索して一致するものがあれば返事をする
    with closing(sqlite3.connect(dbname)) as conn:
        c = conn.cursor()
        create_table = "CREATE TABLE IF NOT EXISTS keywords(keyword, response, username, deleteflag)"
        c.execute(create_table)
        sql = "select response from keywords where ? like '%'||keyword||'%' and deleteflag=0"
        word = (message.content,)
        for row in c.execute(sql, word):
            if row[0] != "":
                await message.channel.send(row[0])

@client.event
async def on_raw_reaction_add(payload):
    guild_id = payload.guild_id
    guild = discord.utils.find(lambda g: g.id == guild_id, client.guilds)

    role = discord.utils.find(lambda r: r.name == payload.emoji.name, guild.roles)

    if role is not None:
        print(role.name + " was found!")
        print(role.id)
        member = discord.utils.find(lambda m: m.id == payload.user_id, guild.members)
        await member.add_roles(role)
        print("done")

@client.event
async def on_raw_reaction_remove(payload):
    guild_id = payload.guild_id
    guild = discord.utils.find(lambda g: g.id == guild_id, client.guilds)
    role = discord.utils.find(lambda r: r.name == payload.emoji.name, guild.roles)

    if role is not None:
        member = discord.utils.find(lambda m: m.id == payload.user_id, guild.members)
        await member.remove_roles(role)
        print("done")

client.run("とーくん")
