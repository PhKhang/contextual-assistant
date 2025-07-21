from openai import OpenAI


class VectorStoreService:
    def __init__(self, client: OpenAI = None, vector_store_id: str = None):
        self._client = client
        self._vector_store_id = vector_store_id

    def update_file(self, deleting_id, file_stream):
        """Updates a file in the vector store.
        Args:
            deleting_id: The ID of the file to be deleted before updating.
            file_stream: A file-like object to upload.
        Returns:
            The ID of the updated file.
        """
        if not self._client or not self._vector_store_id:
            raise ValueError(
                "Client and vector store ID must be set before updating files."
            )

        try:
            self._client.files.delete(deleting_id)
        except Exception as e:
            print(f"Error deleting file {deleting_id}: {e}")

        return self.upload_file(file_stream)

    def upload_file(self, file_stream):
        """Uploads a single file to the vector store.
        Args:
            file_stream: A file-like object to upload.
        Returns:
            The ID of the uploaded file.
        """
        if not self._client or not self._vector_store_id:
            raise ValueError(
                "Client and vector store ID must be set before uploading files."
            )

        # Upload
        result = self._client.files.create(
            file=file_stream,
            purpose="assistants",
        )

        # Add file id to vector store
        self._client.vector_stores.file_batches.create(
            vector_store_id=self._vector_store_id, file_ids=[result.id]
        )

        return result.id

    def delete_file(self, file_id):
        if not self._client or not self._vector_store_id:
            raise ValueError(
                "Client and vector store ID must be set before deleting files."
            )
        try:
            if file_id:
                self._client.files.delete(file_id)
        except Exception as e:
            print(f"Error deleting file {file_id}: {e}")
            pass

    def retrieve(self, query: str, top_k: int = 5):
        if not self._client or not self._vector_store_id:
            raise ValueError(
                "Client and vector store ID must be set before retrieving data."
            )
        response = self._client.vector_stores.search(
            vector_store_id=self._vector_store_id, query=query, max_num_results=top_k
        )

        return response.data if response and hasattr(response, "data") else []
