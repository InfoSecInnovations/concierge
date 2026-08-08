import {
	ChatModelSelector,
	ModelSelectionFallback,
	resolveModelSelection,
} from "./chatModelSelector";

export const ModelManagementForm = async () => {
	const { selection, chatModels, selectedChatModels } =
		await resolveModelSelection({
			fallback: ModelSelectionFallback.AllChatModels,
		});
	return (
		<form action="/manage-models" method="post">
			<fieldset>
				<legend>LLM Configuration</legend>
				<ChatModelSelector
					selectId="manage_language_model"
					containerId="manage_default_model_selector"
					required
					chatModels={chatModels}
					selectedChatModels={selectedChatModels}
					defaultModel={selection.defaultModel}
				>
					The language models which will be available to users when querying
					Shabti. Selecting a model which isn't installed yet will download it,
					and deselecting one removes it from Shabti.
				</ChatModelSelector>
				<p>
					The embeddings model in use is{" "}
					<strong>{selection.embeddingsModel}</strong>, which can only be
					changed by reinstalling as changing it would invalidate all existing
					ingested documents.
				</p>
				<p>
					Removing a model doesn't delete the downloaded files, so you can add
					it back again without waiting for another download. If you want to
					reclaim the disk space you will have to remove the Llama.cpp service,
					which deletes all of the downloaded models.
				</p>
				<p>
					Applying changes restarts the LLM service, so Shabti will be unable to
					answer queries for a short while.
				</p>
				<button type="submit">Apply Model Changes</button>
			</fieldset>
		</form>
	);
};
