from api.main import NentWorker
from database.main import DataBase


def main():
    DataBase().init()
    NentWorker().run()


main()
