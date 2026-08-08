export const UninstallForm = () => (
	// the id is what wireUninstallConfirmation in the client bundle hooks the confirmation onto
	<form action="/uninstall" method="post" id="uninstall_form">
		<fieldset>
			<legend>Uninstall</legend>
			<p>
				This removes all of the Shabti Docker services and the configuration on
				this system. All document collections and the documents they contain
				will be permanently lost.
			</p>
			<p>
				<input
					type="checkbox"
					id="delete_model_files"
					name="delete_models"
				></input>
				<label for="delete_model_files">Delete language model files</label>
			</p>
			<p>
				Leaving this unchecked keeps the models you've already downloaded, so a
				future install won't have to fetch them again.
			</p>
			<button type="submit">Uninstall Shabti</button>
		</fieldset>
	</form>
);
