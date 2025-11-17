import API


if __name__ == "__main__":
    api = API.webAPI()
    try :
        api.start()
        while True:
            pass
    except KeyboardInterrupt:
        print("KeyboardInterrupt received")
        api.close()