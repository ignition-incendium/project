"""Database module."""

__all__ = [
    "DisposableConnection",
    "InParam",
    "OutParam",
    "Param",
    "check",
    "execute_non_query",
    "get_data",
    "get_output_params",
    "get_return_value",
]

import system.db
import system.util
from com.inductiveautomation.ignition.common import BasicDataset
from java.lang import Thread


class DisposableConnection(object):
    """Disposable Connection.

    A disposable connection enables a database connection in Ignition
    and disables it once the operation is completed to release
    resources.
    """

    def __init__(self, database, retries=3):
        """Disposable Connection initializer.

        Args:
            database (str): The name of the database connection in
                Ignition.
            retries (int): The number of additional times to retry
                enabling the connection. Optional.
        """
        super(DisposableConnection, self).__init__()
        self._database = database
        self._retries = retries
        self._global_conn = "incendium_db_{}".format(database)

    @property
    def database(self):
        """Get the name of the disposable connection."""
        return self._database

    @property
    def status(self):
        """Get connection status."""
        connection_info = system.db.getConnectionInfo(self._database)
        return str(connection_info.getValueAt(0, "Status"))

    def __enter__(self):
        """Enter the runtime context related to this object."""
        system.db.setDatasourceEnabled(self.database, True)

        for _ in range(self._retries):
            Thread.sleep(1000)
            if self.status == "Valid":
                if self._global_conn not in system.util.globals:
                    system.util.globals[self._global_conn] = 0
                system.util.globals[self._global_conn] += 1
                break
            if self.status == "Faulted":
                raise IOError(
                    "The database connection {!r} is {}.".format(
                        self._database, self.status
                    )
                )
        else:
            raise IOError(
                "The database connection {!r} could not be enabled.".format(
                    self._database
                )
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the runtime context related to this object."""
        system.util.globals[self._global_conn] -= 1
        if system.util.globals[self._global_conn] == 0:
            system.db.setDatasourceEnabled(self._database, False)


class Param(object):
    """Base class used for defining [IN|OUT]PUT parameters."""

    def __init__(self, name_or_index=None, type_code=None, value=None):
        """Param object initializer.

        Args:
            name_or_index (object): Parameter name or index.
            type_code (int): Type code constant.
            value (object): Value of type type_code.
        """
        super(Param, self).__init__()
        self._name_or_index = name_or_index
        self._type_code = type_code
        self._value = value

    @property
    def name_or_index(self):
        """Get value of name_or_index."""
        return self._name_or_index

    @property
    def type_code(self):
        """Get value of type_code."""
        return self._type_code

    @property
    def value(self):
        """Get value of value."""
        return self._value

    def __repr__(self):
        """Compute the "official" string representation."""
        return "{}(name_or_index={!r}, type_code={!r}, value={!r})".format(
            self.__class__.__name__,
            self.name_or_index,
            self.type_code,
            self.value,
        )

    def __str__(self):
        """Compute the "informal" string representation."""
        return "{!r}, {!r}, {!r}".format(self.name_or_index, self.type_code, self.value)


class InParam(Param):
    """Class used for declaring INPUT parameters."""

    def __init__(self, name_or_index, type_code, value):
        """Create an instance of InParam.

        Args:
            name_or_index (object): Index (int starting at 1, not 0), or
                name (str).
            type_code (int): Type code constant from `system.db`.
            value (object): Value of type type_code.
        """
        super(InParam, self).__init__(
            name_or_index=name_or_index, type_code=type_code, value=value
        )


class OutParam(Param):
    """Class used for declaring OUTPUT parameters."""

    def __init__(self, name_or_index, type_code):
        """Create an instance of OutParam.

        Args:
            name_or_index (object): Index (int starting at 1, not 0), or
                name (str).
            type_code (int): Type code constant from `system.db`.
        """
        super(OutParam, self).__init__(name_or_index=name_or_index, type_code=type_code)


def _execute_sp(
    stored_procedure,
    database="",
    transaction=None,
    skip_audit=False,
    in_params=None,
    out_params=None,
    get_out_params=False,
    get_result_set=False,
    get_ret_val=False,
    get_update_count=False,
    return_type_code=None,
):
    """Execute a stored procedure against the connection.

    Args:
        stored_procedure (str): The name of the stored procedure to
            execute.
        database (str): The name of the database connection to execute
            against. If omitted or "", the project's default database
            connection will be used. Optional.
        transaction (str): A transaction identifier. If omitted, the
            call will be executed in its own transaction. Optional.
        skip_audit (bool): A flag which, if set to True, will cause the
            procedure call to skip the audit system. Useful for some
            queries that have fields which won't fit into the audit log.
            Optional.
        in_params (list[InParam]): A Dictionary containing INPUT
            parameters. Optional.
        out_params (list[OutParam]): A Dictionary containing OUTPUT
            parameters. Optional.
        get_out_params (bool): A flag indicating whether or not to
            return OUTPUT parameters after execution. Optional.
        get_result_set (bool): A flag indicating whether or not to
            return a dataset that is the resulting data of the stored
            procedure, if any. Optional.
        get_ret_val (bool): A flag indicating whether or not to return
            the return value of the stored procedure Call. Optional.
        get_update_count (bool): A flag indicating whether or not to
            return the number of rows modified by the stored
            procedure, or -1 if not applicable. Optional.
        return_type_code (int): The return value Type Code. Optional.

    Returns:
        dict: Result dictionary.
    """
    call = system.db.createSProcCall(
        procedureName=stored_procedure,
        database=database,
        tx=transaction,
        skipAudit=skip_audit,
    )

    if in_params is not None:
        for i_param in in_params:
            call.registerInParam(
                i_param.name_or_index, i_param.type_code, i_param.value
            )

    if out_params is not None:
        for o_param in out_params:
            call.registerOutParam(o_param.name_or_index, o_param.type_code)

    if get_ret_val:
        call.registerReturnParam(return_type_code)

    system.db.execSProcCall(call)

    _out_params = {}
    if out_params is not None and get_out_params:
        for o_param in out_params:
            _out_params[o_param.name_or_index] = call.getOutParamValue(
                o_param.name_or_index
            )

    return {
        "output_params": _out_params,
        "result_set": call.getResultSet() if get_result_set else BasicDataset(),
        "return_value": call.getReturnValue() if get_ret_val else None,
        "update_count": call.getUpdateCount() if get_update_count else -1,
    }


def get_output_params(
    stored_procedure, output, database="", transaction=None, params=None
):
    """Get the Output parameters from the Stored Procedure.

    Args:
        stored_procedure (str): The name of the stored procedure to
            execute.
        output (list[OutParam]): A list containing all OUTPUT parameters
            as OutParam objects.
        database (str): The name of the database connection to execute
            against. If omitted or "", the project's default database
            connection will be used. Optional.
        transaction (str): A transaction identifier. If omitted, the
            call will be executed in its own transaction. Optional.
        params (list[InParam]): A list containing all INPUT parameters
            as InParam objects. Optional.

    Returns:
        dict: A Python dictionary of OUTPUT parameters.
    """
    result = _execute_sp(
        stored_procedure,
        database=database,
        transaction=transaction,
        in_params=params,
        out_params=output,
        get_out_params=True,
    )

    return result["output_params"]


def check(stored_procedure, database="", params=None):
    """Execute a stored procedure against the connection.

    This will return a flag set to TRUE or FALSE.

    Args:
        stored_procedure (str): The name of the stored procedure to
            execute.
        database (str): The name of the database connection to execute
            against. If omitted or "", the project's default database
            connection will be used. Optional.
        params (list[InParam]): A list containing all INPUT parameters
            as InParam objects. Optional.

    Returns:
        bool: The flag.
    """
    output = OutParam("flag", system.db.BIT)
    output_params = get_output_params(
        stored_procedure, output=[output], database=database, params=params
    )

    return output_params["flag"] if "flag" in output_params.iterkeys() else None


def execute_non_query(stored_procedure, database="", transaction=None, params=None):
    """Execute a stored procedure against the connection.

    Used for UPDATE, INSERT, and DELETE statements.

    Args:
        stored_procedure (str): The name of the stored procedure to
            execute.
        database (str): The name of the database connection to execute
            against. If omitted or "", the project's default database
            connection will be used. Optional.
        transaction (str): A transaction identifier. If omitted, the
            call will be executed in its own transaction. Optional.
        params (list[InParam]): A list containing all INPUT parameters
            as InParam objects. Optional.

    Returns:
        int: The number of rows modified by the stored procedure, or
            -1 if not applicable.
    """
    result = _execute_sp(
        stored_procedure,
        database=database,
        transaction=transaction,
        in_params=params,
        get_update_count=True,
    )

    return result["update_count"]


def get_data(stored_procedure, database="", params=None):
    """Get data by executing a stored procedure.

    Args:
        stored_procedure (str): The name of the stored procedure to
            execute.
        database (str): The name of the database connection to execute
            against. If omitted or "", the project's default database
            connection will be used. Optional.
        params (list[InParam]): A list containing all INPUT parameters
            as InParam objects. Optional.

    Returns:
        BasicDataset: A Dataset that is the resulting data of the stored
            procedure call.
    """
    result = _execute_sp(
        stored_procedure,
        database=database,
        in_params=params,
        get_result_set=True,
    )

    return result["result_set"]


def get_return_value(
    stored_procedure,
    return_type_code,
    database="",
    transaction=None,
    params=None,
):
    """Get the Return Value from the Stored Procedure.

    Args:
        stored_procedure (str): The name of the stored procedure to
            execute.
        return_type_code (int): The Type Code of the Return Value.
        database (str): The name of the database connection to execute
            against. If omitted or "", the project's default database
            connection will be used. Optional.
        transaction (str): A transaction identifier. If omitted, the
            call will be executed in its own transaction. Optional.
        params (list[InParam]): A list containing all INPUT parameters
            as InParam objects. Optional.

    Returns:
        int: The return value.
    """
    result = _execute_sp(
        stored_procedure,
        database=database,
        transaction=transaction,
        in_params=params,
        get_ret_val=True,
        return_type_code=return_type_code,
    )

    return result["return_value"]


def o_execute_non_query(
    stored_procedure, out_params, database="", transaction=None, in_params=None
):
    """Execute a stored procedure against the connection.

    Used for UPDATE, INSERT, and DELETE statements which return OUTPUT
    parameters.

    Args:
        stored_procedure (str): The name of the stored procedure to
            execute.
        out_params (list[OutParam]): A list containing all OUTPUT
            parameters as OutParam objects.
        database (str): The name of the database connection to execute
            against. If omitted or "", the project's default database
            connection will be used. Optional.
        transaction (str): A transaction identifier. If omitted, the
            call will be executed in its own transaction. Optional.
        in_params (list[InParam]): A list containing all INPUT
            parameters as InParam objects. Optional.

    Returns:
        tuple: A tuple containing the number of rows modified by the
            stored procedure, or -1 if not applicable, and the OUTPUT
            parameters as a dictionary.
    """
    result = _execute_sp(
        stored_procedure,
        database=database,
        transaction=transaction,
        in_params=in_params,
        out_params=out_params,
        get_out_params=True,
        get_update_count=True,
    )

    return result["update_count"], result["output_params"]


def o_get_data(stored_procedure, out_params, database="", in_params=None):
    """Get data by executing a stored procedure and OUTPUT parameters.

    Args:
        stored_procedure (str): The name of the stored procedure to
            execute.
        out_params (list[OutParam]): A list containing all OUTPUT
            parameters as OutParam objects.
        database (str): The name of the database connection to execute
            against. If omitted or "", the project's default database
            connection will be used. Optional.
        in_params (list[InParam]): A list containing all INPUT
            parameters as InParam objects. Optional.

    Returns:
        tuple: A tuple containing a Dataset that is the resulting data
            of the stored procedure call, and the OUTPUT parameters as a
            Python dictionary.
    """
    result = _execute_sp(
        stored_procedure,
        database=database,
        in_params=in_params,
        out_params=out_params,
        get_out_params=True,
        get_result_set=True,
    )

    return result["result_set"], result["output_params"]
