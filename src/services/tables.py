import os

import psycopg2


def get_stories(limit=10):
    host = os.environ["REPLICA_HOST"]
    database = os.environ["REPLICA_DB"]
    user = os.environ["REPLICA_USER"]
    password = os.environ["REPLICA_PASSWORD"]

    conn = psycopg2.connect(host=host, database=database, user=user, password=password)
    query = (
        """
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
        AND st.type != 'SEGMENT'
    ORDER BY
        st.published_at DESC
    LIMIT %s;
    """
        % limit
    )

    try:
        # Open a cursor to perform database operations
        cur = conn.cursor()

        # Execute the query
        cur.execute(query)

        # Fetch all the results
        result = cur.fetchall()

        # Convert result into a dictionary {table_name: row_count}
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

        # Close the cursor and connection
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
        # Open a cursor to perform database operations
        cur = conn.cursor()

        # Execute the query
        cur.execute(query)

        # Fetch all the results
        result = cur.fetchall()

        # Convert result into a dictionary {table_name: row_count}
        table_row_count_dict = {row[0]: row[1] for row in result}

        # Close the cursor and connection
        cur.close()
        conn.close()

        return table_row_count_dict

    except Exception as e:
        print(f"An error occurred: {e}")
        return {}


# Usage
if __name__ == "__main__":
    print(get_stories())
    # print(get_table_row_counts())
