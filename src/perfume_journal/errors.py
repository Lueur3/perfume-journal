class DuplicatePerfumeError(Exception):
    pass


class PerfumeNotFoundError(Exception):
    pass


class CollectionItemNotFoundError(Exception):
    pass


class CollectionItemArchivedError(Exception):
    pass


class CollectionItemHasWearingsError(Exception):
    pass


class PerfumeHasCollectionItemsError(Exception):
    pass


class WearingNotFoundError(Exception):
    pass
