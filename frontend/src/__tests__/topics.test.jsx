import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { STUDENT, TEACHER, fakeBackend, renderApp } from "./helpers.jsx";

const COURSE = { id: 1, title: "Programming Fundamentals", description: null, join_code: "ABC234", teacher_name: "Ms. Khan" };
const LOOP_MESSAGE = 'That would make a loop: "Variables" needs "Loops" needs "Variables".';

/**
 * A pretend backend that really keeps topics, so adding, moving and deleting change what loads next.
 * Start with [{ id, title, parent_id, prerequisite_ids }], in the order they were added.
 * extraRoutes: other pages' routes, e.g. the course page's assignment list.
 */
function topicsBackend({ user = TEACHER, topics = [], courseResponse, prerequisiteResponse, extraRoutes = {} } = {}) {
  let list = topics.map((t) => ({ parent_id: null, prerequisite_ids: [], ...t }));
  let nextId = 100;

  const nest = (parentId) =>
    list.filter((t) => t.parent_id === parentId).map((t) => ({ ...t, children: nest(t.id) }));
  const inside = (id) => [id, ...list.filter((t) => t.parent_id === id).flatMap((t) => inside(t.id))];

  const routes = {
    ...extraRoutes,
    "GET /api/auth/me": [200, user],
    "GET /api/courses/1": courseResponse || [200, COURSE],
    "GET /api/courses/1/topics": () => [200, nest(null)],
    // Order added is fine here: the real topological sort is tested in the backend.
    "GET /api/courses/1/topics/study-order": () => [200, list.map(({ id, title, parent_id, prerequisite_ids }) => ({ id, title, parent_id, prerequisite_ids }))],
    "POST /api/courses/1/topics": (options) => {
      const body = JSON.parse(options.body);
      const topic = { id: nextId++, parent_id: null, prerequisite_ids: [], ...body };
      list.push(topic);
      return [201, topic];
    },
  };
  // Routes for each topic id that exists now or may be created in a test.
  for (const id of [...list.map((t) => t.id), 100, 101]) {
    routes[`PATCH /api/topics/${id}`] = (options) => {
      const topic = list.find((t) => t.id === id);
      Object.assign(topic, JSON.parse(options.body));
      return [200, topic];
    };
    routes[`DELETE /api/topics/${id}`] = () => {
      const gone = inside(id);
      list = list.filter((t) => !gone.includes(t.id));
      return [204]; // no body, like the real 204
    };
    routes[`POST /api/topics/${id}/prerequisites`] = (options) => {
      if (prerequisiteResponse) return prerequisiteResponse;
      const topic = list.find((t) => t.id === id);
      topic.prerequisite_ids = [...topic.prerequisite_ids, JSON.parse(options.body).prerequisite_id];
      return [201, { topic_id: id, prerequisite_ids: topic.prerequisite_ids }];
    };
    for (const other of list.map((t) => t.id)) {
      routes[`DELETE /api/topics/${id}/prerequisites/${other}`] = () => {
        const topic = list.find((t) => t.id === id);
        topic.prerequisite_ids = topic.prerequisite_ids.filter((p) => p !== other);
        return [204]; // no body, like the real 204
      };
    }
  }
  return fakeBackend(routes);
}

// Python basics → Loops → For loops, and Variables (Loops needs Variables)
const SAMPLE = [
  { id: 1, title: "Python basics" },
  { id: 2, title: "Loops", parent_id: 1, prerequisite_ids: [4] },
  { id: 3, title: "For loops", parent_id: 2 },
  { id: 4, title: "Variables" },
];

function calls(fetchMock, method, path) {
  return fetchMock.mock.calls.filter(([p, options]) => p === path && options?.method === method);
}

function bodyOf(fetchMock, method, path) {
  const [call] = calls(fetchMock, method, path);
  return call ? JSON.parse(call[1].body) : undefined;
}

/** The tree card on the page (the study order lists the same titles). */
async function treeCard() {
  const heading = await screen.findByRole("heading", { name: "Topic tree" });
  return within(heading.closest("section"));
}

async function openEditor(user, title) {
  await user.click(await screen.findByRole("button", { name: `Edit ${title}` }));
  return within(screen.getByRole("button", { name: "Done" }).closest(".topic-editor"));
}

afterEach(() => {
  vi.restoreAllMocks();
});

// ---------- students ----------

describe("topics page (student)", () => {
  it("shows the nested tree, each topic's prerequisites, and the study order", async () => {
    topicsBackend({ user: STUDENT, topics: SAMPLE });
    renderApp("/courses/1/topics", { loggedInAs: STUDENT });

    const tree = await treeCard();
    const basics = (await tree.findByText("Python basics")).closest("li");
    const loops = within(basics).getByText("Loops").closest("li");
    expect(within(loops).getByText("For loops")).toBeInTheDocument(); // nested two levels deep
    expect(within(loops).getAllByText("Needs: Variables")[0]).toBeInTheDocument();

    const order = within(screen.getByRole("heading", { name: "Study order" }).closest("section"));
    expect(order.getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "Python basics",
      "Loops after Variables",
      "For loops",
      "Variables",
    ]);
  });

  it("has no editing controls", async () => {
    topicsBackend({ user: STUDENT, topics: SAMPLE });
    renderApp("/courses/1/topics", { loggedInAs: STUDENT });

    await (await treeCard()).findByText("Python basics");
    expect(screen.queryByRole("heading", { name: "Add a topic" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Edit/ })).not.toBeInTheDocument();
  });

  it("says when there are no topics yet", async () => {
    topicsBackend({ user: STUDENT });
    renderApp("/courses/1/topics", { loggedInAs: STUDENT });

    expect(await screen.findByText("Your teacher hasn't added any topics.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Study order" })).not.toBeInTheDocument();
  });

  it("is reached from the course page", async () => {
    topicsBackend({ user: STUDENT, topics: SAMPLE, extraRoutes: { "GET /api/courses/1/my-work": [200, []] } });
    renderApp("/courses/1", { loggedInAs: STUDENT });
    const user = userEvent.setup();

    await user.click(await screen.findByRole("link", { name: /Topics and study order/ }));

    expect(await screen.findByRole("heading", { name: "Topics" })).toBeInTheDocument();
  });

  it("shows the backend's message for a course you're not in", async () => {
    topicsBackend({ user: STUDENT, courseResponse: [404, { detail: "Course not found." }] });
    renderApp("/courses/1/topics", { loggedInAs: STUDENT });

    expect(await screen.findByRole("alert")).toHaveTextContent("Course not found.");
    expect(screen.queryByRole("heading", { name: "Topic tree" })).not.toBeInTheDocument();
  });
});

// ---------- teachers ----------

describe("topics page (teacher)", () => {
  it("adds a top-level topic, then a subtopic inside it", async () => {
    const fetchMock = topicsBackend();
    renderApp("/courses/1/topics", { loggedInAs: TEACHER });
    const user = userEvent.setup();

    await user.type(await screen.findByLabelText("Title"), "Python basics");
    await user.click(screen.getByRole("button", { name: "Add topic" }));
    const tree = await treeCard();
    expect(await tree.findByText("Python basics")).toBeInTheDocument();
    expect(bodyOf(fetchMock, "POST", "/api/courses/1/topics")).toEqual({ title: "Python basics" });

    await user.selectOptions(screen.getByLabelText("Put inside"), "Python basics");
    await user.type(screen.getByLabelText("Title"), "Loops");
    await user.click(screen.getByRole("button", { name: "Add topic" }));

    const basics = (await tree.findByText("Loops")).closest("ul").closest("li");
    expect(within(basics).getByText("Python basics")).toBeInTheDocument();
    expect(JSON.parse(calls(fetchMock, "POST", "/api/courses/1/topics")[1][1].body)).toEqual({ title: "Loops", parent_id: 100 });
  });

  it("asks for a title before sending", async () => {
    const fetchMock = topicsBackend();
    renderApp("/courses/1/topics", { loggedInAs: TEACHER });
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Add topic" }));

    expect(screen.getByText("Enter a topic title.")).toBeInTheDocument();
    expect(calls(fetchMock, "POST", "/api/courses/1/topics")).toHaveLength(0);
  });

  it("renames a topic, sending only the title", async () => {
    const fetchMock = topicsBackend({ topics: SAMPLE });
    renderApp("/courses/1/topics", { loggedInAs: TEACHER });
    const user = userEvent.setup();

    const editor = await openEditor(user, "Loops");
    await user.clear(editor.getByLabelText("Title"));
    await user.type(editor.getByLabelText("Title"), "Loops and ranges");
    await user.click(editor.getByRole("button", { name: "Save" }));

    expect(await (await treeCard()).findByText("Loops and ranges")).toBeInTheDocument();
    expect(bodyOf(fetchMock, "PATCH", "/api/topics/2")).toEqual({ title: "Loops and ranges" });
  });

  it("moves a topic to the top level with parent_id null", async () => {
    const fetchMock = topicsBackend({ topics: SAMPLE });
    renderApp("/courses/1/topics", { loggedInAs: TEACHER });
    const user = userEvent.setup();

    const editor = await openEditor(user, "For loops");
    await user.selectOptions(editor.getByLabelText("Put inside"), "Top level (no parent)");
    await user.click(editor.getByRole("button", { name: "Save" }));

    await vi.waitFor(() => expect(bodyOf(fetchMock, "PATCH", "/api/topics/3")).toEqual({ parent_id: null }));
  });

  it("doesn't offer moving a topic inside itself or its subtopics", async () => {
    topicsBackend({ topics: SAMPLE });
    renderApp("/courses/1/topics", { loggedInAs: TEACHER });
    const user = userEvent.setup();

    const editor = await openEditor(user, "Python basics");
    const options = within(editor.getByLabelText("Put inside")).getAllByRole("option").map((o) => o.textContent);

    expect(options).toEqual(["Top level (no parent)", "Variables"]);
  });

  it("adds a prerequisite and shows it", async () => {
    const fetchMock = topicsBackend({ topics: SAMPLE });
    renderApp("/courses/1/topics", { loggedInAs: TEACHER });
    const user = userEvent.setup();

    const editor = await openEditor(user, "For loops");
    await user.selectOptions(editor.getByLabelText("Prerequisite to add"), "· Loops");
    await user.click(editor.getByRole("button", { name: "Add prerequisite" }));

    expect(await editor.findByRole("button", { name: "Remove Loops" })).toBeInTheDocument();
    expect(bodyOf(fetchMock, "POST", "/api/topics/3/prerequisites")).toEqual({ prerequisite_id: 2 });
    const forLoops = (await treeCard()).getByText("For loops").closest("li");
    expect(within(forLoops).getByText("Needs: Loops")).toBeInTheDocument();
  });

  it("doesn't offer a topic itself or an existing prerequisite", async () => {
    topicsBackend({ topics: SAMPLE });
    renderApp("/courses/1/topics", { loggedInAs: TEACHER });
    const user = userEvent.setup();

    const editor = await openEditor(user, "Loops");
    const options = within(editor.getByLabelText("Prerequisite to add")).getAllByRole("option").map((o) => o.textContent);

    expect(options).toEqual(["Choose a topic…", "Python basics", "· · For loops"]);
  });

  it("shows the loop message when the backend refuses a prerequisite", async () => {
    topicsBackend({ topics: SAMPLE, prerequisiteResponse: [409, { detail: LOOP_MESSAGE }] });
    renderApp("/courses/1/topics", { loggedInAs: TEACHER });
    const user = userEvent.setup();

    const editor = await openEditor(user, "Variables");
    await user.selectOptions(editor.getByLabelText("Prerequisite to add"), "· Loops");
    await user.click(editor.getByRole("button", { name: "Add prerequisite" }));

    expect(await editor.findByRole("alert")).toHaveTextContent(LOOP_MESSAGE);
  });

  it("removes a prerequisite", async () => {
    const fetchMock = topicsBackend({ topics: SAMPLE });
    renderApp("/courses/1/topics", { loggedInAs: TEACHER });
    const user = userEvent.setup();

    const editor = await openEditor(user, "Loops");
    await user.click(editor.getByRole("button", { name: "Remove Variables" }));

    expect(await editor.findByText("No prerequisites.")).toBeInTheDocument();
    expect(calls(fetchMock, "DELETE", "/api/topics/2/prerequisites/4")).toHaveLength(1);
  });

  it("deletes a topic and its subtopics after confirming", async () => {
    const fetchMock = topicsBackend({ topics: SAMPLE });
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    renderApp("/courses/1/topics", { loggedInAs: TEACHER });
    const user = userEvent.setup();

    const editor = await openEditor(user, "Python basics");
    await user.click(editor.getByRole("button", { name: "Delete topic" }));

    expect(confirm).toHaveBeenCalledWith(
      'Delete "Python basics" and the 2 subtopics inside it? This can\'t be undone.',
    );
    const tree = await treeCard();
    await vi.waitFor(() => expect(tree.queryByText("Python basics")).not.toBeInTheDocument());
    expect(tree.queryByText("For loops")).not.toBeInTheDocument();
    expect(tree.getByText("Variables")).toBeInTheDocument();
    expect(calls(fetchMock, "DELETE", "/api/topics/1")).toHaveLength(1);
  });

  it("keeps the topic when deleting is cancelled", async () => {
    const fetchMock = topicsBackend({ topics: SAMPLE });
    vi.spyOn(window, "confirm").mockReturnValue(false);
    renderApp("/courses/1/topics", { loggedInAs: TEACHER });
    const user = userEvent.setup();

    const editor = await openEditor(user, "Variables");
    await user.click(editor.getByRole("button", { name: "Delete topic" }));

    expect(calls(fetchMock, "DELETE", "/api/topics/4")).toHaveLength(0);
    expect((await treeCard()).getByText("Variables")).toBeInTheDocument();
  });
});
