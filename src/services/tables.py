import os
import datetime
import httpx
import uuid

import psycopg2


def get_attributes():
    return [
        {"name": "title", "default": True},
        {"name": "text", "default": True},
        {"name": "published_at", "default": False},
        {"name": "publication", "default": False},
        {"name": "author", "default": False},
        {"name": "type", "default": False},
        {"name": "classification", "default": False},
    ]


def get_stories(start_date, limit=10):
    host = os.environ["REPLICA_HOST"]
    database = os.environ["REPLICA_DB"]
    user = os.environ["REPLICA_USER"]
    password = os.environ["REPLICA_PASSWORD"]
    if not isinstance(limit, int):
        raise ValueError("limit should be an integer")
    if limit < 1:
        raise ValueError("limit should be greater than 0")
    if limit > 100000:
        raise ValueError("limit should be less than 100000")

    conn = psycopg2.connect(host=host, database=database, user=user, password=password)
    query = f"""
    SELECT
        st.id, st.title, s.text, st.published_at, p.name as publication, st.author, st.type, st.classification
    FROM
        content_story st
    INNER JOIN
        scripts_script s on s.story_id = st.id
    INNER JOIN
        content_publication p on p.id = st.publication_id
    WHERE
        st.published_at::date <= current_date 
        AND st.published_at::date >= '{start_date}'  
        AND (st.type != 'SEGMENT' OR st.type IS NULL)
    ORDER BY
        st.published_at DESC
    LIMIT ({limit});
    """

    try:
        cur = conn.cursor()
        cur.execute(query)
        result = cur.fetchall()
        table_row_count_dict = [
            {
                "id": row[0],
                "title": row[1],
                "text": row[2],
                "published_at": row[3],
                "publication": row[4],
                "author": row[5],
                "type": row[6],
                "classification": row[7],
            }
            for row in result
        ]
        cur.close()
        conn.close()
        return {"total": len(table_row_count_dict), "data": table_row_count_dict}
    except Exception as e:
        print(f"An error occurred: {e}")
        return {}


def get_table_row_counts(
    host=os.environ["REPLICA_HOST"],
    database=os.environ["REPLICA_DB"],
    user=os.environ["REPLICA_USER"],
    password=os.environ["REPLICA_PASSWORD"],
):
    # Database connection details (you can load these from environment variables)
    conn = psycopg2.connect(host=host, database=database, user=user, password=password)

    # Query to get table names and row counts from public schema
    query = """
    SELECT
        relname AS table_name,
        n_live_tup AS row_count
    FROM
        pg_stat_user_tables
    WHERE
        schemaname = 'public'
    ORDER BY
        row_count DESC;
    """

    try:
        cur = conn.cursor()
        cur.execute(query)
        result = cur.fetchall()
        table_row_count_dict = {row[0]: row[1] for row in result}
        cur.close()
        conn.close()
        return table_row_count_dict
    except Exception as e:
        print(f"An error occurred: {e}")
        return {}


def get_stories_by_id(story_ids):
    host = os.environ["REPLICA_HOST"]
    database = os.environ["REPLICA_DB"]
    user = os.environ["REPLICA_USER"]
    password = os.environ["REPLICA_PASSWORD"]

    # do security check on the list and make sure it's a list of uuids
    if not isinstance(story_ids, list):
        raise ValueError("story_ids should be a list of story ids")
    for story_id in story_ids:
        try:
            uuid.UUID(story_id, version=4)
        except ValueError:
            raise ValueError("story_ids should be a list of valid story ids")

    story_ids_placeholder = ", ".join(["%s"] * len(story_ids))

    conn = psycopg2.connect(host=host, database=database, user=user, password=password)

    query = f"""
        SELECT
            st.id, st.title, s.text, st.published_at, p.name as publication, st.author, st.type, st.classification
        FROM
            content_story st
        INNER JOIN
            scripts_script s on s.story_id = st.id
        INNER JOIN
            content_publication p on p.id = st.publication_id
        WHERE
            st.id IN ({story_ids_placeholder})
        ORDER BY
            st.published_at DESC;
    """

    try:
        cur = conn.cursor()
        cur.execute(query, (*story_ids,))
        result = cur.fetchall()
        table_row_count_dict = [
            {
                "id": row[0],
                "title": row[1],
                "text": row[2],
                "published_at": row[3],
                "publication": row[4],
                "author": row[5],
                "type": row[6],
                "classification": row[7],
            }
            for row in result
        ]

        cur.close()
        conn.close()

        return {"total": len(table_row_count_dict), "data": table_row_count_dict}

    except Exception as e:
        print(f"An error occurred: {e}")
        return {}


def get_vector_search_stories(start_date, limit, query):
    end_date_time = datetime.datetime.now().isoformat()
    vector_db_url = "http://13.92.253.7"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {
        "query": str(query),
        "n_results": limit,
        "start_date_time": start_date,
        "end_date_time": end_date_time,
    }
    response = httpx.post(
        f"{vector_db_url}/search_articles/", headers=headers, json=payload
    )
    response.raise_for_status()
    return response.json()[0]
