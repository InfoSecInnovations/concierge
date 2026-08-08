import type { Child } from "hono/jsx";

// the tab label doubles as the heading, so with only one tab there's nothing to switch
// between and we render it as a plain section with its title
export const Tabs = (props: {
	tabs: { id: string; label: string; content: Child }[];
}) => {
	const [first, ...rest] = props.tabs;
	if (!first) return <></>;
	if (!rest.length)
		return (
			<section>
				<h3>{first.label}</h3>
				{first.content}
			</section>
		);
	return (
		<>
			<nav class="tabs" id="tab_nav">
				{props.tabs.map((tab, i) => (
					<button
						type="button"
						class={i ? "tab" : "tab active"}
						data-tab={tab.id}
					>
						{tab.label}
					</button>
				))}
			</nav>
			{props.tabs.map((tab, i) => (
				<section id={tab.id} class={i ? "tab_panel hidden" : "tab_panel"}>
					{tab.content}
				</section>
			))}
		</>
	);
};
