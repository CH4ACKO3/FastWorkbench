package dev.shadowsoffire.fastbench.util;

import net.minecraft.world.inventory.CraftingContainer;
import net.minecraft.world.inventory.ResultContainer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.level.Level;

/** Validates cached recipes against the manager's current matching table after reloads. */
final class RecipeCache {

    private RecipeCache() {}

    private static Recipe<?> registered(Recipe<?> candidate, Level level) {
        // Use the matching table, not byKey: script-driven reloads may update these independently.
        var recipes = level.getRecipeManager().recipes.get(candidate.getType());
        return recipes == null ? null : recipes.get(candidate.getId());
    }

    static Recipe<?> current(ResultContainer result, Level level) {
        Recipe<?> cached = result.getRecipeUsed();
        if (cached != null && !level.isClientSide && registered(cached, level) != cached) {
            result.setRecipeUsed(null);
            result.setItem(0, ItemStack.EMPTY);
            return null;
        }
        return cached;
    }

    @SuppressWarnings("unchecked")
    static Recipe<CraftingContainer> resolve(Recipe<CraftingContainer> candidate, CraftingContainer input, Level level) {
        // Recipe-selection integrations may themselves retain an object from before /reload.
        if (candidate != null) {
            Recipe<CraftingContainer> current = (Recipe<CraftingContainer>) registered(candidate, level);
            if (current != null && current.matches(input, level)) return current;
        }
        return level.getRecipeManager().getRecipeFor(RecipeType.CRAFTING, input, level).orElse(null);
    }
}
