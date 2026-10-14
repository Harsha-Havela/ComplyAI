"""
Database Module
Handles all database operations and connections
"""
import sqlite3
import os
from flask import g, current_app


def get_db():
    """
    Get database connection.
    Creates a new connection if not exists in current context.
    
    Returns:
        sqlite3.Connection: Database connection object
    """
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE_PATH'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    """
    Close database connection.
    Automatically called at the end of each request.
    
    Args:
        e: Exception if any
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """
    Initialize database with schema.
    Creates all tables and indexes if they don't exist.
    """
    db = get_db()
    
    # Read and execute schema
    schema_path = os.path.join(
        os.path.dirname(__file__), 
        'schema.sql'
    )
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        db.executescript(f.read())
    
    db.commit()


def query_db(query, args=(), one=False):
    """
    Execute SELECT query and return results.
    
    Args:
        query: SQL query string
        args: Query parameters tuple
        one: If True, return single row; else return all rows
        
    Returns:
        Single row dict or list of row dicts
    """
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    
    if rv:
        if one:
            return dict(rv[0])
        return [dict(row) for row in rv]
    return None if one else []


def execute_db(query, args=()):
    """
    Execute INSERT, UPDATE, DELETE query.
    
    Args:
        query: SQL query string
        args: Query parameters tuple
        
    Returns:
        int: Last inserted row ID or number of affected rows
    """
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    
    last_id = cur.lastrowid
    rows_affected = cur.rowcount
    cur.close()
    
    return last_id if last_id > 0 else rows_affected


def init_app(app):
    """
    Register database functions with Flask app.
    
    Args:
        app: Flask application instance
    """
    app.teardown_appcontext(close_db)
