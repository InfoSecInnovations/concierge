import getDefaultModelSelection from "../getDefaultModelSelection";
import getModelsConfig from "../getModelsConfig";
import readModelsIni from "./readModelsIni";

export const ModelManagementForm = async () => {
	const shabtiModels = await getModelsConfig();
	const selection =
		(await readModelsIni()) || (await getDefaultModelSelection());
	const chatModels = Object.entries(shabtiModels)
		.filter(([_, v]) => v.tags.includes("chat"))
		.map(([k]) => k);
	const selectedChatModels = chatModels.filter((model) =>
		selection.chatModels.includes(model),
	);
	return (
		<form action="/manage-models" method="post">
			<fieldset>
				<legend>LLM Configuration</legend>
				<p>
					<label for="manage_language_model">Select Chat Models</label>
					<select
						name="language_model"
						id="manage_language_model"
						multiple
						required
					>
						{chatModels.map((model) => (
							<option
								value={model}
								selected={selectedChatModels.includes(model)}
							>
								{model}
							</option>
						))}
					</select>
					The language models which will be available to users when querying
					Shabti. Selecting a model which isn't installed yet will download it,
					and deselecting one removes it from Shabti.
				</p>
				<div id="manage_default_model_selector">
					{selectedChatModels.length > 1 && (
						<p>
							<label for="manage_default_model_selector_select">
								Default Chat Model
							</label>
							<select
								id="manage_default_model_selector_select"
								name="default_model"
							>
								{selectedChatModels.map((model) => (
									<option
										value={model}
										selected={model == selection.defaultModel}
									>
										{model}
									</option>
								))}
							</select>
							This model will be selected by default unless the user chooses a
							different one.
						</p>
					)}
				</div>
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
