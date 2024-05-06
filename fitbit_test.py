# Sessionを使わず、import requestsでもOKです
from requests import Session
from pprint import pprint
import json

session = Session()

with open("./test_conf.json", "r", encoding="utf-8") as f:
    conf = json.load(f)


def bearer_header():
    """Bearer認証用ヘッダ
    Returns:
        dict: {"Authorization":"Bearer " + your-access-token}
    """
    return {"Authorization": "Bearer " + conf["access_token"]}


def refresh():
    """
    access_tokenを再取得し、conf.jsonを更新する。
    refresh_tokenは再取得に必要なので重要。
    is_expiredがTrueの時のみ呼ぶ。
    False時に呼んでも一式更新されるので、実害はない。
    """

    url = "https://api.fitbit.com/oauth2/token"

    # client typeなのでclient_idが必要
    params = {
        "grant_type": "refresh_token",
        "refresh_token": conf["refresh_token"],
        "client_id": conf["client_id"],
    }

    # POST実行。 Body部はapplication/x-www-form-urlencoded。requestsならContent-Type不要。
    res = session.post(url, data=params)

    # responseをパース
    res_data = res.json()

    # errorあり
    if res_data.get("errors") is not None:
        emsg = res_data["errors"][0]
        print(emsg)
        return

    # errorなし。confを更新し、ファイルを更新
    conf["access_token"] = res_data["access_token"]
    conf["refresh_token"] = res_data["refresh_token"]
    with open("./test_conf.json", "w", encoding="utf-8") as f:
        json.dump(conf, f, indent=2)


def is_expired(resObj) -> bool:
    """
    Responseから、accesss-tokenが失効しているかチェックする。
    失効ならTrue、失効していなければFalse。Fitbit APIでは8時間が寿命。
    Args:
        reqObj (_type_): response.json()したもの

    Returns:
        boolean: 失効ならTrue、失効していなければFalse
    """

    errors = resObj.get("errors")

    # エラーなし。
    if errors is None:
        return False

    # エラーあり
    for err in errors:
        etype = err.get("errorType")
        if (etype is None):
            continue
        if etype == "expired_token":
            pprint("TOKEN_EXPIRED!!!")
            return True

    # 失効していないのでFalse。エラーありだが、ここでは制御しない。
    return False


def request(method, url, **kw):
    """
    sessionを通してリクエストを実行する関数。
    アクセストークンが8Hで失効するため、失効時は再取得し、
    リクエストを再実行する。
    レスポンスはパースしないので、呼ぶ側で.json()なり.text()なりすること。

    Args:
        method (function): session.get,session.post...等
        url (str): エンドポイント
        **kw: headers={},params={}を想定

    Returns:
        session.Response: レスポンス
    """

    # パラメタで受け取った関数を実行し、jsonでパース
    res = method(url, **kw)
    res_data = res.json()

    if is_expired(res_data):
        # 失効していしている場合、トークンを更新する
        refresh()
        # headersに設定されているトークンも
        # 新しい内容に更新して、methodを再実行
        kw["headers"] = bearer_header()
        res = method(url, **kw)
    # parseしていないほうを返す
    return res


def heartbeat(date: str = "today", period: str = "1d"):
    """心拍数を取得しレスポンスを返す。パースはしない。

    Args:
        date (str, optional): 取得する日付。yyyy-mm-ddで指定も可能。Defaults to "today".
        period (str, optional): 取得する範囲。1d,7d,30d,1w,1m。 Defaults to "1d".

    Returns:
        session.Response: レスポンス
    """
    # パラメタを埋め込んでエンドポイント生成
    # url = f"https://api.fitbit.com/1/user/-/activities/heart/date/{date}/{period}.json"
    # url = f"https://api.fitbit.com/1/user/-/hrv/date/{date}/all.json"
    # url = f"https://api.fitbit.com/1/user/-/spo2/date/2024-01-01/2024-01-03/all.json" # not good
    # url = f"https://api.fitbit.com/1/user/-/spo2/date/{date}/all.json"
    # url = f"https://api.fitbit.com/1/user/-/temp/core/date/{date}.json" # nothing
    # url = f"https://api.fitbit.com/1/user/-/activities/date/{date}.json"
    # url = f"https://api.fitbit.com/1/user/-/temp/skin/date/{date}.json"
    url = f" https://api.fitbit.com/1.2/user/-/sleep/date/{date}.json"

    # 認証ヘッダ取得
    headers = bearer_header()

    # 自作のリクエスト関数に渡す
    res = request(session.get, url, headers=headers)

    return res


# 実行例
res = heartbeat()
data = res.json()
pprint(data)


import json

with open('./data.json', 'w') as file:
    json.dump(data, file, ensure_ascii=False)