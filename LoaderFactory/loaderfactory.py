from LoaderFactory import abstract_loader
class Loaderfactory:
    def __init__(self):
        pass

    def getLoader(self, name) ->abstract_loader.AbstractLoader():

        if name == "mango":
            from LoaderFactory import temporary_loader
            return temporary_loader.MangoLoader()

        if name == "skorozvon":
            from LoaderFactory import skorozvon_loader
            return skorozvon_loader.SkorozvonLoader()

        if name == "beeline":
            from LoaderFactory import beeline_loader
            return beeline_loader.BeelineLoader()

        if name == "kcell":
            from LoaderFactory import kcell_loader
            return kcell_loader.KCellLoader()
        if name=="megaphone":
            from LoaderFactory import megaphone_loader
            return megaphone_loader.Megaphone_Loader()


