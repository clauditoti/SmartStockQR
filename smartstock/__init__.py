import pymysql

# Le decimos que se identifique como una versión moderna
pymysql.version_info = (2, 2, 2, "final", 0)

pymysql.install_as_MySQLdb() 
