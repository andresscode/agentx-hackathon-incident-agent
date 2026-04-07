"use server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export type Todo = {
  id: number;
  title: string;
};

export async function getTodos(): Promise<Todo[]> {
  const res = await fetch(`${BACKEND_URL}/api/todos`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch todos");
  return res.json();
}

export async function addTodo(title: string): Promise<Todo> {
  const res = await fetch(`${BACKEND_URL}/api/todos`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error("Failed to create todo");
  return res.json();
}

export async function deleteTodo(id: number): Promise<void> {
  const res = await fetch(`${BACKEND_URL}/api/todos/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete todo");
}
