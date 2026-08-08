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
					Shabti.
				</ChatModelSelector>
				<p>
					<label>Current Embeddings Model</label>{" "}
					<strong>{selection.embeddingsModel}</strong>. You cannot change the
					embeddings model as this would invalidate all currently ingested
					documents.
				</p>
				<button type="submit">Apply Model Changes</button>
			</fieldset>
		</form>
	);
};
