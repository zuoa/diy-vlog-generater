from flask import jsonify


def resp_data(data=None, code=0, message="success"):
    wrapper_data = {
        "success": code == 0,
        "code": code,
        "data": data,
        "message": message
    }
    return jsonify(wrapper_data)


def resp_page_list(list_, total, page):
    data = {
        "list": list_,
        "total": total,
        "page": page,
    }

    return resp_data(data)


def success(data=None):
    return resp_data(data)


def error(code, message):
    return resp_data(code=code, message=message)

