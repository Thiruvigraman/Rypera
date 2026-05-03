# file: database/__init__.py

from .connection import (
    MONGO_AVAILABLE,
    db
)
from .movies import (
    load_movies,
    load_movies_full,
    load_movies_cached,
    save_movie,
    get_movie_by_token,
    delete_movie,
    rename_movie,
    increment_movie_access,
    get_top_movies
)

from .users import (
    add_user,
    get_all_users,
    remove_user
)

from .stats import (
    get_stats,
    get_db_size_mb
)

from .sent_files import (
    save_sent_file,
    get_pending_files,
    delete_sent_file_record
)

from .access_logs import (
    save_access_log,
    get_unsent_logs,
    mark_log_sent,
    setup_log_ttl
)

from .groups import (
    create_group,
    get_group_by_token,
    increment_group_access,
    search_groups,
    get_all_groups
)


def is_db_available():
    return MONGO_AVAILABLE