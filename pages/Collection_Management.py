import json
import streamlit as st
from concierge_streamlit_lib.collections import EnsureCollections, GetExistingCollectionCached, CreateCollectionWidget, DropCollection, COLLECTIONS
from concierge_streamlit_lib.status import SidebarStatus

st.set_page_config(page_title="Concierge AI: Collection Management", layout="wide")

# ---- first run only ----

EnsureCollections()

# ---- main loop ----

SidebarStatus()

site_list = []
array_counter = {}
file_list = []


try:
    selected_collection = st.query_params["collection"]
except:
    selected_collection = ''

if selected_collection:
    st.write('# Collections Manager')
    # CreateCollectionWidget()
    try:
        collection = GetExistingCollectionCached(selected_collection)
    except:
        collection = ''
    
    if (collection):
        with st.container(border=1):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"### '{selected_collection}' Collection")
                entity_count = collection.num_entities
                st.write("<span data-toggle='tooltip' title='Entity count refers to the number of reference points created in the collection'>Entity count</span>: ", entity_count, unsafe_allow_html=True)
                pdf_count = collection.query( expr = "metadata_type == 'pdf'",
                                             output_fields = ["count(*)"],
                                             )[0]['count(*)']
                st.write("<span data-toggle='tooltip' title='Entity count refers to the number of reference points created in the collection'>PDF based count</span>: ", pdf_count, unsafe_allow_html=True)
                web_count = collection.query( expr = "metadata_type == 'web'",
                                             output_fields = ["count(*)"],
                                             )[0]['count(*)']
                st.write("<span data-toggle='tooltip' title='Entity count refers to the number of reference points created in the collection'>Web based count</span>: ", web_count, unsafe_allow_html=True)
            with col2:
                st.write(f"### PDF Documents")
                #
                #################################################
                #
                # Lets index all the PDF files
                # 
                #
                #
                pdf_iterator = collection.query_iterator( batch_size = 100, 
                                                        expr = "metadata_type == 'pdf'", 
                                                        output_fields = ["metadata_type", "metadata"],
                                                    )
                while True:
                    # turn to the next page
                    pdf_res = pdf_iterator.next()
                    # st.write(pdf_res)
                    if len(pdf_res) == 0:
                        # st.write("Finished Processing")
                        # close the iterator
                        pdf_iterator.close()
                        break
                    for i in range(len(pdf_res)):
                        file_type = pdf_res[i]["metadata_type"]
                        file_name = json.loads(pdf_res[i]["metadata"])['filename']
                        # st.write(f"DEBUG", file_name, file_list)
                        if file_name not in (file_list):
                            file_list.append(file_name)
                            array_counter[file_name] = {"count": 1}
                        else:
                            array_counter[file_name]['count'] += 1
                file_total = len(file_list)
                st.write(f"Total Files Indexed: ", file_total)
                with st.expander("Files Indexed - Entities Created  "):
                    for file_entry in file_list:
                        cur_file = file_entry
                        st.write(cur_file, array_counter[cur_file]['count'])

            with col3:
                st.write(f"### Web Sites")
                #
                #################################################
                #
                # Lets index all the web files
                # this is not efficient.  This does not scale
                #
                web_iterator = collection.query_iterator( batch_size = 20, 
                                                            expr = "metadata_type == 'web'", 
                                                            output_fields = ["metadata_type", "metadata"],
                                                        )
                while True:
                    # turn to the next page
                    web_res = web_iterator.next()
                    # st.write(web_res)
                    if len(web_res) == 0:
                        # st.write("Finished Processing")
                        # close the iterator
                        web_iterator.close()
                        break
                    for i in range(len(web_res)):
                        site_name = json.loads(web_res[i]["metadata"])['source']
                        # st.write(f"DEBUG", site_name, site_list)
                        if site_name not in (site_list):
                            site_list.append(site_name)
                            array_counter[site_name] = {"count": 1}
                        else:
                            array_counter[site_name]['count'] += 1
                web_total = len(site_list)
                st.write(f"Total Web Sites Indexed: ", web_total)
                with st.expander("Websites Indexed - Entities Created"):
                    for site_entry in site_list:
                        cur_site = site_entry
                        st.write(cur_site, array_counter[cur_site]['count'])
                #
                ######################
                #
                # put the delete button on the page
                #
                #
                st.button("delete collection", key=f"delete_{selected_collection}", on_click=DropCollection, args=[selected_collection])


    else:
        st.write(f"### Collection \"" + selected_collection + "\" does not exist")

else:
    st.write('# Collections Manager')

    CreateCollectionWidget()

    for collection_name in st.session_state[COLLECTIONS]:
        collection = GetExistingCollectionCached(collection_name)

        with st.container(border=1):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"### Collection: [{collection_name}](/Collection_Management?collection={collection_name} 'Collection Details')")
                st.write("<span data-toggle='tooltip' title='Entity count refers to the number of references created in the collection'>Entity count</span>: ", collection.num_entities, unsafe_allow_html=True)
                
            with col2:
                st.button("delete collection", key=f"delete_{collection_name}", on_click=DropCollection, args=[collection_name])