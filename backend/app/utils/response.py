from fastapi.responses import JSONResponse

class ResponseWrapper:
    @staticmethod
    def _resolve_error_status_code(code: int) -> int:
        return 500 if code == 500 or code >= 500000 else 400

    @staticmethod
    def success(data=None, msg="success", code=0):
        return JSONResponse(content={
            "code": code,
            "msg": msg,
            "data": data
        })

    @staticmethod
    def error(msg="error", code=500, data=None, status_code=None):
        resolved_status = status_code or ResponseWrapper._resolve_error_status_code(code)
        return JSONResponse(status_code=resolved_status, content={
            "code": code,
            "msg": str(msg),
            "data": data
        })
