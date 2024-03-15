import decimal
import json
import operator
import os
import random
import numpy as np
import pytz
import requests
from flask import Flask, jsonify, Response, request
from flask_cors import CORS
import time
import datetime
from flask_apscheduler import APScheduler


app = Flask(__name__)
app.config['SCHEDULER_API_ENABLED'] = True
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()
CORS(app, resources=r"/gacha/*")
cardList = []
process_finish = []
cardDict = [{}, {}, {}, {}, {}]
cardTypeInPool = {0: ['all'], 1: ['permanent']}
cardTemp = {}
currentActive = []
cardCount = [0, 0, 0, 0, 0]
AllCard = {}
percentagePool = {}
char_list = ["","戸山香澄","花園たえ","牛込りみ","山吹沙綾",
      "市ヶ谷有咲","美竹蘭","青葉モカ","上原ひまり","宇田川巴","羽沢つぐみ",
      "弦巻こころ","瀬田薫","北沢はぐみ","松原花音","ミッシェル","丸山彩",
      "氷川日菜","白鷺千聖","大和麻弥","若宮イヴ","湊友希那","氷川紗夜",
      "今井リサ","宇田川あこ","白金燐子","倉田ましろ","桐ヶ谷透子",
      "広町七深","二葉つくし","八潮瑠唯","和奏レイ","朝日六花",
      "佐藤ますき","鳰原令王那","珠手ちゆ"]



# print(random.choices([1,2,3,4],cardPercent[0]))
with open("activity.json", "r", encoding="utf-8") as f:
    config = json.load(f)
with open("all.5.json", "r", encoding="utf-8") as f:
    content = json.load(f)

for k, item in content.items():
    direct_train = False
    if ("training" in item["stat"]) and item["stat"]['training']['levelLimit'] == 0:
        direct_train = True

    if item["releasedAt"][0] == None:
        continue
    if not os.path.exists("gacha_json/" + str(k) + ".json"):
        continue
    with open("gacha_json/" + str(k) + ".json", "r", encoding="utf-8") as f:
        temp = json.load(f)
        cardList.append({"cid": temp['characterId'], "type": temp['attribute'], "resource": temp['resourceSetName'],
                         "star": temp['rarity'], "slog": temp['gachaText'][0], "id": int(k), "title": temp['prefix'][0],
                         "card_type": temp['type'], "direct_train": direct_train})
        AllCard[int(k)] = {"cid": temp['characterId'], "type": temp['attribute'], "resource": temp['resourceSetName'],
                         "star": temp['rarity'], "slog": temp['gachaText'][0], "id": int(k), "title": temp['prefix'][0],
                         "card_type": temp['type'], "direct_train": direct_train,"prefix":item['prefix'][0]}

for card in cardList:
    card_indexs = 5 - card['star']
    if card_indexs < 0:
        card_indexs = -card_indexs

    if card["card_type"] not in cardDict[card_indexs]:
        cardDict[card_indexs][card['card_type']] = []
    cardDict[card_indexs][card['card_type']].append(card)


#初始化所有数据并写入缓存
def process():
    # 初始化所有数据并写入缓存
    for tempk, tempitem in config.items():
        if int(tempk) in process_finish:
            continue
        else:
            process_finish.append(int(tempk))
        percentage = {}
        new_card_list = [[], [], [], [], []]

        if "card_type" in config[tempk]:
            all_in = config[tempk]['card_type'][0]
            if all_in == "all":
                all_in = True
            else:
                all_in = False

        for kii in range(4):
            index = abs(kii - 5)
            if ('card_in_pool' in config[tempk]) and (str(index) in config[tempk]['card_in_pool']):
                new_card_list[kii] = config[tempk]['card_in_pool'][str(index)]
            else:
                for card_t, listCard in cardDict[kii].items():
                    if (all_in == True) or (card_t in config[tempk]['card_type']):
                        for card_ in listCard:
                            new_card_list[kii].append(int(card_['id']))
                            continue

            if ("card_extend" in config[tempk] and (str(index) in config[tempk]['card_extend'])):
                if config[tempk]['card_extend'][str(index)] not in new_card_list[kii]:
                    for extend_cards in config[tempk]['card_extend'][str(index)]:
                        if extend_cards not in new_card_list[kii]:
                            new_card_list[kii].append(extend_cards)

        cardTemp[tempk] = new_card_list

        # 得到每个卡的概率
        for ki in range(5):
            thiscard = False
            star = abs(ki - 5)
            percentage[ki] = {}
            percentage[ki]['common'] = []
            percentage[ki]['up'] = []
            card_up = {}
            card_up_up = {}
            oc_percentage = decimal.Decimal(0.0)
            oc_up_percentage = 0
            oc_total_card = 0
            oc_up_total_card = 0
            total_card = len(new_card_list[ki])

            # if ki == 1:
            # print(total_card)
            # print(new_card_list[ki])
            if total_card == 0:
                continue

            if "up" in config[tempk] and str(star) in config[tempk]['up']['common']:
                for card_up_percentage, card_up_item in config[tempk]['up']['common'][str(star)].items():
                    for card_up_item_id in card_up_item:
                        card_up[card_up_item_id] = card_up_percentage

                        oc_percentage += decimal.Decimal(card_up_percentage)
                        # if ki == 1:
                        #     print(oc_percentage)
                        oc_total_card += 1
                        if ki <= 3:
                            oc_up_total_card += 1
                if "up" in config[tempk]['up'] and str(star) in config[tempk]['up']['up']:
                    for card_up_percentage, card_up_item in config[tempk]['up']['up'][str(star)].items():
                        for card_up_item_id in card_up_item:
                            card_up_up[card_up_item_id] = card_up_percentage
                            oc_up_percentage += float(card_up_percentage)
            # print(float(oc_percentage))
            common_percard_percent = float(
                (decimal.Decimal(config[tempk]["card_percent"][ki]) - oc_percentage) / decimal.Decimal(
                    ((total_card) - oc_total_card)))
            # print(common_percard_percent)
            up_percard_percent = 0
            if ki == 2:
                up_percard_percent = ((config[tempk]["card_percent"][2] + config[tempk]["card_percent"][
                    3]) - oc_up_percentage) / (total_card - oc_up_total_card)
            else:
                up_percard_percent = common_percard_percent

            # if "activity_card" in config[tempk]:
            # if star in config[tempk]['activity_card']:
            #     thiscard = True
            #     total_activity_card = len(config[tempk]["activity_card"][star])

            # common_percard_percent = ((config[tempk]["card_percent"][ki]) - (
            #         total_activity_card * config[tempk]["up"][star])) / (
            #                                  total_card - total_activity_card)

            for card_s in new_card_list[ki]:
                if card_s in card_up:
                    percentage[ki]['common'].append(float(card_up[card_s]))
                    if card_s in card_up_up:
                        percentage[ki]['up'].append(float(card_up_up[card_s]))
                    else:
                        percentage[ki]['up'].append(float(card_up[card_s]))
                else:
                    percentage[ki]['common'].append(common_percard_percent)
                    percentage[ki]['up'].append(up_percard_percent)
            percentagePool[tempk] = percentage
process()

















@app.route('/gacha/<id>')
def gacha(id):

    now = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).timestamp()

    ten = request.args.get("ten", "1")
    keep = request.args.get("keep","0")
    keepCard = False
    recruit_time = 0
    if keep == "1":
        keepCard = True
    if ten == "1":
        recruit_time = 10
    else:
        recruit_time = 1

    if str(id).isnumeric():
        id = str(id)
        # 如果概率不在卡池中
        if id not in config:
            return return_Json(-1, [])

        if "activity_start" in config[id]:
            timeArray = time.strptime(config[id]['activity_start'], "%Y-%m-%d %H:%M:%S")
            if time.mktime(timeArray) > now:
                return return_Json(-1, [f"活动未开始,开始日期JST(日本时间)-{config[id]['activity_start']}"])
        if "activity_end" in config[id]:
            timeArray = time.strptime(config[id]['activity_end'], "%Y-%m-%d %H:%M:%S")
            if time.mktime(timeArray) < now:
                return return_Json(-1, [f"活动过期,截止日期JST(日本时间)-{config[id]['activity_end']}"])
        cards = getCards(recruit_time, id,keepCard)
        return return_Json(0, cards)

    return return_Json(-1, [])

@app.route('/gacha/list')
def gacha_list():
    list_arr = []
    now = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).timestamp()
    for k,item in config.items():
        if "activity_start" in item:
            timeArray = time.strptime(item['activity_start'], "%Y-%m-%d %H:%M:%S")
            if time.mktime(timeArray) > now:
                continue
        if "activity_end" in item:
            timeArray = time.strptime(item['activity_end'], "%Y-%m-%d %H:%M:%S")
            if time.mktime(timeArray) < now:
                continue
        if "activity_start" not in item:
            activity_start = None
        else:
            activity_start = item['activity_start']
        if "activity_end" not in item:
            activity_end = None
        else:
            activity_end = item['activity_end']
        activity_kira = False
        if "activity_kira" in item:
            activity_kira = item['activity_kira']
        list_char = [[],[],[],[],[]]
        card_list = cardTemp[k]
        for i in range(5):
            # print(AllCard)
            for ki, citem in enumerate(card_list[i]):

                card = AllCard[citem]
                list_char[i].append({"t":card['type'],"c":card['cid'],"n":card['prefix'],"p":percentagePool[k][i]['common'][ki],"p_up":percentagePool[k][i]['up'][ki]})
        list_arr.append({"pool_percentage":config[k]['card_percent'][0:4],"activity_id":k,"meta":item["meta"],"time_start":activity_start,"time_end":activity_end,"char":list_char,"kira":activity_kira})






    return return_Json(200,list_arr)

@app.route("/gacha/test")
def gacha_test():
    result = []
    for k,item in AllCard.items():
        if item['star'] == 2 and item['cid']==13 and item["card_type"]=="permanent":
            result.append(item)

    return return_Json(200,result)

def getCardImg(tc):
    if tc['direct_train'] == True:
         return f"https://bestdori.com/assets/jp/characters/resourceset/{tc['resource']}_rip/card_after_training.png"
    else:
        return f"https://bestdori.com/assets/jp/characters/resourceset/{tc['resource']}_rip/card_normal.png"


def return_Json(code, data):
    return json.dumps({"status": code, "data": data})
def get_url_data(url):
    return requests.get(url).content
def save_for_image(bytes,path,name):
    if not os.path.exists("apply/card_img/"+path):
        os.makedirs("apply/card_img/"+path)
    with open("apply/card_img/"+path+"/"+name,"wb") as f:
        f.write(bytes)
        f.close()

def getCards(recruit_time, pool,keepCard):
    myCard = []
    myCardCommon = []
    percentage = {}
    activity = False

    if "activity_card" in config[pool] and len(config[pool]["activity_card"]) != 0:
        activity = True

    bad = True
    randomPool = config[pool]['card_percent'][0:4]
    # 得到每个卡的概率
    percentage = percentagePool[pool]
    new_card_list = cardTemp[pool]
    for i in range(recruit_time):
        # print(randomPool)
        card_level_index = random.choices([0, 1, 2, 3], randomPool)



        # print((percentage[0]/np.sum(percentage[0]))*config[pool]["card_percent"][0])
        # if card_level_index[0] == 1:
        #     print(np.sum(percentage[card_level_index[0]]['common']))
            # print(percentage[card_level_index[0]]['common'])
            # count = decimal.Decimal(0)
            # for idsx in percentage[card_level_index[0]]['common']:
            #     count += decimal.Decimal(idsx)
            # print(count)
            # print(new_card_list[card_level_index[0]])
        card_id = random.choices(new_card_list[card_level_index[0]],percentage[card_level_index[0]]['common'])

        card = AllCard[card_id[0]]
        myCard.append(card)
        if card['star'] >= 3:
            bad = False
        else:
            myCardCommon.append(i)
    # 小保底
    if keepCard:
        if activity:

            keep = random.choice(config[pool]["activity_card"][str(5)])
            myCard[0] = AllCard[keep]
            try:
                myCardCommon.pop(0)
            except:
                a = ""
    #保底
    if recruit_time == 10 and len(myCardCommon)!=0:

        random_common_card_index = random.choice(myCardCommon)

        new_percent = randomPool

        new_percent[2] += new_percent[3]
        new_percent[3] = 0

        card_level_index = random.choices([0, 1, 2, 3], new_percent)
        # print(random.choices(new_card_list[card_level_index[0]], percentage[card_level_index[0]]))
        # if card_level_index[0] == 2:
            # print(np.sum(percentage[card_level_index[0]]['up']))
        myCard[random_common_card_index] = AllCard[random.choices(new_card_list[card_level_index[0]],percentage[card_level_index[0]]['up'])[0]]

    return myCard

@scheduler.task("interval",id="update_pool", seconds=5)
def update_pool_t():
    content = requests.get("https://bestdori.com/api/gacha/all.5.json").json()
    array_for_temp = []
    gacha_ids = []
    publishTimeLimit = 1689832800000
    card_json = requests.get("https://bestdori.com/api/cards/all.5.json").json()
    with open("all.5.json", "w", encoding='utf-8') as f:
        json.dump(card_json, f, indent=2, sort_keys=True, ensure_ascii=False)

    for k, items in card_json.items():
        if items['releasedAt'][0] == None:
            continue
        if int(k) in AllCard:
            continue


        direct_train = False
        if ("training" in items["stat"]) and items["stat"]['training']['levelLimit'] == 0:
            direct_train = True

        have_update = False
        if items['rarity'] >= 3:
            have_update = True
        resource_name = items['resourceSetName']
        card_position = str(int(k) // 50)
        while len(card_position) < 5:
            card_position = f"0{card_position}"

        if direct_train != True:
            card_normal = get_url_data(
                f'https://bestdori.com/assets/jp/characters/resourceset/{resource_name}_rip/card_normal.png')
            save_for_image(card_normal, "card/" + resource_name, "card_normal.png")

            card_normal_thumb = get_url_data(
                f'https://bestdori.com/assets/jp/thumb/chara/card{card_position}_rip/{resource_name}_normal.png')
            save_for_image(card_normal_thumb, "thumb/" + resource_name, f'{resource_name}_normal.png')
        if have_update:
            card_after = get_url_data(
                f'https://bestdori.com/assets/jp/characters/resourceset/{resource_name}_rip/card_after_training.png')
            save_for_image(card_after, "card/" + resource_name, "card_after_training.png")
            card_after_thumb = get_url_data(
                f'https://bestdori.com/assets/jp/thumb/chara/card{card_position}_rip/{resource_name}_after_training.png')
            save_for_image(card_after_thumb, "thumb/" + resource_name, f'{resource_name}_after_training.png')

        card_information = requests.get(f"https://bestdori.com/api/cards/{k}.json").json()
        with open(f'gacha_json/{k}.json', "w", encoding="utf-8") as fc:
            json.dump(card_information, fc, ensure_ascii=False)
        AllCard[int(k)] = {"cid": card_information['characterId'], "type": card_information['attribute'],
                           "resource": card_information['resourceSetName'],
                           "star": card_information['rarity'], "slog": card_information['gachaText'][0], "id": int(k),
                           "title": card_information['prefix'][0],
                           "card_type": card_information['type'], "direct_train": direct_train,
                           "prefix": items['prefix'][0]}
        cardList.append({"cid": temp['characterId'], "type": temp['attribute'], "resource": temp['resourceSetName'],
                         "star": temp['rarity'], "slog": temp['gachaText'][0], "id": int(k), "title": temp['prefix'][0],
                         "card_type": temp['type'], "direct_train": direct_train})

    for k, items in content.items():
        allow_type = ["limited", 'kirafes', 'permanent', 'birthday', 'dreamfes']
        if items['publishedAt'][0] == None:
            continue
        if items['type'] not in allow_type:
            continue

        array_for_temp.append({"gachaId": int(k), "publishTime": int(items['publishedAt'][0])})
    array_for_temp.sort(key=operator.itemgetter("publishTime"), reverse=True)

    for item in array_for_temp:
        gid = item['gachaId']
        if str(gid) not in config and item['publishTime'] >= publishTimeLimit:
            gacha_ids.append(gid)

    # print(gacha_ids)


    if len(gacha_ids) == 0:
        return


    for ids in gacha_ids:
        poolId = ids

        gacha = {}
        content = requests.get(f"https://bestdori.com/api/gacha/{poolId}.json").json()
        with open("apply/gacha/" + str(poolId) + ".json", "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False)

        gacha['meta'] = {}
        gacha['meta']['logo_src'] = f"https://bestdori.com/assets/jp/gacha/screen/gacha{poolId}_rip/logo.png"
        # 目前缺陷，img需要手动指定
        gacha['meta']['img_src'] = None
        gacha['meta']['name'] = content['gachaName'][0]
        gacha['card_in_pool'] = {}

        gacha['activity_kira'] = False
        if content['type'] == "permanent":
            gacha['activity_kira'] = True
        gacha['meta']['des'] = content['information']['description'][0]
        gacha['card_percent'] = [0, 0, 0, 0, 0]
        gacha['activity_end'] = datetime.datetime.now().fromtimestamp(int(content['closedAt'][0]) / 1000,
                                                                      tz=pytz.timezone('Asia/Tokyo')).strftime(
            "%Y-%m-%d %H:%M:%S")
        gacha['activity_start'] = datetime.datetime.now().fromtimestamp(int(content['publishedAt'][0]) / 1000,
                                                                      tz=pytz.timezone('Asia/Tokyo')).strftime(
            "%Y-%m-%d %H:%M:%S")

        gacha_t = []
        gacha_thread = 0
        for k, item in content['details'][0].items():
            if str(item['rarityIndex']) not in gacha['card_in_pool']:
                gacha['card_in_pool'][str(item['rarityIndex'])] = []
            gacha['card_in_pool'][str(item['rarityIndex'])].append(int(k))

            if item['pickup'] == True:

                if "activity_card" not in gacha:
                    gacha['activity_card'] = {}
                if str(item['rarityIndex']) not in gacha['activity_card']:
                    gacha['activity_card'][str(item['rarityIndex'])] = []
                gacha['activity_card'][str(item['rarityIndex'])].append(int(k))




                if "up" not in gacha or "common" not in gacha['up']:
                    gacha['up'] = {}
                    gacha['up']['common'] = {}
                if str(item['rarityIndex']) not in gacha['up']['common']:
                    gacha['up']['common'][str(item['rarityIndex'])] = {}
                rates = str((item['weight'] / content['rates'][0][str(item['rarityIndex'])]['weightTotal']) *
                            content['rates'][0][str(item['rarityIndex'])]['rate'])
                # print(gacha_thread)
                if gacha_thread < int(item['rarityIndex']):
                    gacha_thread = int(item['rarityIndex'])
                    # print(int(item['rarityIndex']))
                    gacha_t = []
                if gacha_thread == int(item['rarityIndex']):
                    gacha_t.append({"id": int(k), "rate": float(rates)})

                # print(gacha_t)
                if rates not in gacha['up']['common'][str(item['rarityIndex'])]:
                    gacha['up']['common'][str(item['rarityIndex'])][rates] = []
                gacha['up']['common'][str(item['rarityIndex'])][rates].append(int(k))

        if len(gacha_t) != 0:
            # print("执行")
            gacha_t.sort(key=operator.itemgetter("rate"), reverse=True)
            tc = AllCard[int(gacha_t[0]['id'])]
            gacha['meta']['img_src'] = getCardImg(tc)
            al = False
            for gt in gacha_t:
                ct = AllCard[int(gt['id'])]
                if ct['card_type'] == "kirafes" and al == False:
                    gacha['meta']['img_src'] = getCardImg(ct)
                    al = True




        else:
            gacha['meta']['img_src'] = f"https://bestdori.com/assets/jp/characters/resourceset/res016052_rip/card_normal.png"

        for kr, item_rate in content['rates'][0].items():
            index = abs(int(kr) - 5)
            gacha['card_percent'][int(index)] = float(item_rate['rate'])
        config[str(ids)] = gacha

    process()
    with open("activity.json", "w", encoding='utf-8') as f:
        json.dump(config, f, indent=2, sort_keys=True, ensure_ascii=False)



if __name__ == '__main__':
    app.run(debug=True)



