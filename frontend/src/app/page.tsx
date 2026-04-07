"use client";

import { useEffect, useState } from "react";
import { addTodo, deleteTodo, getTodos, type Todo } from "./actions";

export default function Home() {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getTodos()
      .then(setTodos)
      .finally(() => setLoading(false));
  }, []);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    const todo = await addTodo(title.trim());
    setTodos((prev) => [...prev, todo]);
    setTitle("");
  }

  async function handleDelete(id: number) {
    await deleteTodo(id);
    setTodos((prev) => prev.filter((t) => t.id !== id));
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-black">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow dark:bg-zinc-900">
        <h1 className="mb-6 text-2xl font-bold text-zinc-900 dark:text-zinc-50">
          Todo List
        </h1>

        <form onSubmit={handleAdd} className="mb-6 flex gap-2">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Add a todo..."
            className="flex-1 rounded border border-zinc-300 px-3 py-2 text-zinc-900 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-50"
          />
          <button
            type="submit"
            className="rounded bg-zinc-900 px-4 py-2 text-white hover:bg-zinc-700 dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-300"
          >
            Add
          </button>
        </form>

        {loading ? (
          <p className="text-zinc-500">Loading...</p>
        ) : todos.length === 0 ? (
          <p className="text-zinc-500">No todos yet.</p>
        ) : (
          <ul className="space-y-2">
            {todos.map((todo) => (
              <li
                key={todo.id}
                className="flex items-center justify-between rounded border border-zinc-200 px-3 py-2 dark:border-zinc-700"
              >
                <span className="text-zinc-900 dark:text-zinc-50">
                  {todo.title}
                </span>
                <button
                  onClick={() => handleDelete(todo.id)}
                  className="text-red-500 hover:text-red-700"
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
