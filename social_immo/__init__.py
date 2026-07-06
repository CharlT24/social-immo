"""
Utilise PyMySQL (pur Python, aucune compilation) comme pilote MySQL.
Necessaire sur les hebergements mutualises type o2switch ou gcc est
bloque (mysqlclient exige une compilation C).
"""
try:
    import pymysql

    # Django 5.2 exige "mysqlclient >= 1.4.3" : on fait passer PyMySQL pour
    # une version compatible avant de l'installer comme MySQLdb.
    pymysql.version_info = (1, 4, 6, 'final', 0)
    pymysql.install_as_MySQLdb()
except ImportError:
    # En dev (SQLite) PyMySQL peut etre absent : ce n'est pas bloquant.
    pass
