import os
from typing import Any

from dotenv import load_dotenv
from mssql_python import connect


def connection_value(value: str) -> str:
    return "{" + value.replace("}", "}}") + "}"


def get_connection():
    load_dotenv()
    connection_string = (
        f"Server={connection_value(os.environ['SQL_SERVER'])};"
        f"Database={connection_value(os.environ['SQL_DATABASE'])};"
        f"UID={connection_value(os.environ['SQL_USER'])};"
        f"PWD={connection_value(os.environ['SQL_PASSWORD'])};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )
    return connect(connection_string)

def get_contract_order_details(
    client_id: int,
    contract_id: int,
    order_line: int,
) -> list[dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT TOP (1000)
            co.[client_id],
            co.[contract_id],
            co.[order_line],
            co.[group_id],
            co.[no_tagline],
            mg.[est_in_home_date]
        FROM [mailshark].[dbo].[contract_order] co
        JOIN [mailshark].[dbo].[mailing_group] mg
            ON co.group_id = mg.group_id
        WHERE co.[client_id] = ?
            AND co.[contract_id] = ?
            AND co.[order_line] = ?
        """,
        (client_id, contract_id, order_line),
    )
    rows = cursor.fetchall()
    columns = [column[0] for column in cursor.description]

    cursor.close()
    conn.close()

    return [dict(zip(columns, row)) for row in rows]


def get_contract_order_detail(
    client_id: int,
    contract_id: int,
    order_line: int,
) -> dict[str, Any] | None:
    rows = get_contract_order_details(client_id, contract_id, order_line)
    if not rows:
        return None
    return rows[0]

def insert_art_result(
    client_id: int,
    contract_id: int,
    order_line: int,
    version: int,
    result: str,
) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO dbo.art_results (
            client_id,
            contract_id,
            order_line,
            version,
            result
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (client_id, contract_id, order_line, version, result),
    )
    conn.commit()
    cursor.close()
    conn.close()
