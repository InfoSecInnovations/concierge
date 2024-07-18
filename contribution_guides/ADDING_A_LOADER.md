# Adding a Loader

Loaders are functions which take a source of information such as a file or URL, vectorize the contents and output metadata in a format suitable for ingestion by Concierge.

For examples of the existing loaders, look at the `loaders` directory inside this repository. `base_loader.py` contains the base classes which need to be inherited by the other loaders.

## Relevant Terms

### Document

The top level element, this represents the input to the loader, such as a file or URL.

In the Concierge code base the class `ConciergeDocument` holds all the other elements relating to the document.

`ConciergeDocument.DocumentMetadata` contains the following fields:
    
    type: str
    source: str
    ingest_date: int

and can be extended to hold more metadata fields.

### Page

The document is split into "pages" which can correspond to actual pages or some other division based on the source material. For example when ingesting a URL, the child URLs that are crawled each end up being a page. Some documents such as those belonging to the text ingester only have a single page and the metadata is empty.

So far our loaders have come from the Langchain framework and the splitting into pages is based on how the `load_and_split` function delimits pages. 

> [!NOTE]
> Splitting a document into pages is not the same as splitting the text into chunks for vectorization, this step is performed later on by existing code inside Concierge.

`ConciergeDocument.ConciergePage` is the class that hold the data for a page. The corresponding metadata class is `ConciergeDocument.ConciergePage.PageMetadata`, this base class is empty but can be extended to contain page metadata such as the page number. `ConciergeDocument.ConciergePage` also has a field called `content` which contains the actual text of the page.

## File Loader

The simplest type of loader to implement is one for loading files, as we already have the pipeline in place to accept files as an input. Examples of these are `pdf.py` and `text.py`.

### Implementing The Class

Create a class which inherits from `ConciergeFileLoader` which itself inherits from `ConciergeDocLoader`.

If you need extra metadata fields on top of the ones existant in `ConciergeFileLoader.FileMetaData` and `ConciergeDocument.ConciergePage.PageMetadata` you must extend those classes.

Implement the following method in the class:

    @staticmethod
    def can_load(full_path: str) -> bool:

This will override the abstract base method. Based on the file's path this should return `True` if we want this loader to attempt to handle it, and `False` if not.

Implement the following method in the class:

    @staticmethod
    def load(full_path: str) -> ConciergeDocument:

This is where we will process the document and output it in the format expected by Concierge. `ConciergeDocument` has `metadata` and `pages` fields. 

#### metadata

`metadata` should be `ConciergeFileLoader.FileMetaData` or a class that inherits from it.

You can import `get_current_time` from `base_loader.py` in order to get the date in the correct format for `ingest_date`. 

`source` is usually the full path, and you can get `filename` by doing `Path(full_path).name` (`Path` is from `pathlib`). 

`type` is an identifier we use for the type of document being ingested, please make sure this isn't shared by any other loaders unless all the metadata uses the exact same fields, in which case it would be permissible to have multiple loaders for the same type of document. We may have to improve on this part of the process in the future.

`media_type` is the Media Type (previously called MIME Type) used in the HTTP header when serving the file to the web browser, it defaults to `text/plain` if not specified. For example in the PDF loader we set it to `application/pdf` to allow the browser to display the PDF file contents properly.

#### pages

While there are a variety of ways you could process the files, we recommend looking at the [Langchain Document Loaders](https://python.langchain.com/v0.1/docs/modules/data_connection/document_loaders/) and [Langchain Community Document Loaders](https://python.langchain.com/v0.1/docs/integrations/document_loaders/) as these cover a vast array of data source types and it's likely the file type you wish to ingest is already handled by one of them.

Load and split the document as per the documentation of the loader you're using and map each resulting page to a `ConciergeDocument.ConciergePage` object and its accompanying `ConciergeDocument.ConciergePage.PageMetadata` or derived class object. The `content` field should contain the `page_content` value from the page, and any items you deem important from the `metadata` dictionary can go into the extended page metadata class.

### Adding Your Loader To Concierge

Now you've created the loader class and its metadata classes, you need to tell Concierge to look for it when loading files. 

Open `concierge_backend_lib/loading.py`.

Import your loader class and add it to the `loaders` list, the loaders are checked in the order of this list, so you should leave `TextFileLoader` as the last element as this is (currently) the fallback loader if none of the others work, bear in mind that your loader will take precedence over any of the ones following it.

That's it, if you implemented the class methods properly you should be able to load your new file type!

#### Customizing The Display Of Your Documents In The Web UI

By default the Shiny app will generate links to the ingested files, however it's possible to override this behavior by adding a custom case for the page and document links.

Go to `concierge_shiny/functions.py` and add a statement matching your file type in the `page_link` and/or `doc_link` functions. Use the provided `doc_url` and `md_link` helper functions to create a Markdown formatted link that will load the original document a new tab in the browser.

`page_link` is used for the references in the chatbot interface and `doc_link` displays the document in the collection management screen.