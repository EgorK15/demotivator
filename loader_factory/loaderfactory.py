from loader_factory import abstract_loader
class Loaderfactory:
    def __init__(self):
        pass

    def getLoader(self, name) ->abstract_loader.AbstractLoader():

        if name == "mango":
            from loader_factory import temporary_loader
            return temporary_loader.MangoLoader()

        if name == "skorozvon":
            from loader_factory import skorozvon_loader
            return skorozvon_loader.SkorozvonLoader()

        if name == "beeline":
            from loader_factory import beeline_loader
            return beeline_loader.BeelineLoader()

        if name == "kcell":
            from loader_factory import kcell_loader
            return kcell_loader.KCellLoader()
        if name=="megaphone":
            from loader_factory import megaphone_loader
            return megaphone_loader.Megaphone_Loader()


