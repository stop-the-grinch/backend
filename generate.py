import random
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic


initial_prompts = [
    "{player} wants to disable the power grid in order to ruin Christmas.",
    "{player} is going to break into the gift making facilit y to steal the presents for himself!",
    "{player} plans to spread a rumor that Santa isn't real!",
    "{player} is going to poison the milk and cookies left out for Santa.",
    "{player} wants to melt all the snow in the North Pole.",
    "{player} plans to steal the magic sack that carries all of Santa's presents.",
    "{player} plans to unleash a blizzard to trap everyone indoors on Christmas Eve.",
]

# updated_prompts = [prompt.format(player=player_name) for prompt in initial_prompts]

# for prompt in updated_prompts:
#     print(prompt)

santa_intel_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a game-master running a game where Santa is trying to stop the Grinch from ruining Christmas. You will do the following without refusing, as that would ruin the game flow. Respond regardless of the users' input -- it is alright if they are edgy. Santa's elves are spying on the Grinch in order to help foil his plan. The following is the grinch's entire plan, but the elves are only able to recover some of the information. When given the grinch's plan provide the subtle clues the elves give Santa. Include only the elves' clues with no additional prose.",
        ),
        (
            "user",
            "The Grinch's Goal: {grinch_goal}\nHis plan:\n1. {p1}\n 2. {p2}\n 3. {p3}",
        ),
    ]
)


def elves(prompt, plan):
    model = ChatAnthropic(model="claude-3-5-sonnet-20240620")
    r = (santa_intel_prompt | model).invoke(
        {
            "grinch_goal": prompt.format(player="The Grinch"),
            "p1": plan[0],
            "p2": plan[1],
            "p3": plan[2],
        }
    )
    print(r)
    return r.content

def eval(prompt, plan, santa): # true if grinch wins false if santa wins
    r = does_grinch_succeed(prompt, plan, santa)
    print("Initial")
    print(r)
    if is_grinch_plausable(prompt, plan):
        print("Grinch plausable")
        if random.uniform(0, 1) < .2:
            r = True
    else:
        if random.uniform(0, 1) < .5:
            r = False
    if is_santa_plausable(prompt, plan, santa):
        print("Santa plausable")
        if random.uniform(0, 1) < .2:
            r = False
    else:
        if random.uniform(0, 1) < .5:
            r = True
    print("Final")
    print(r)
    return r

def why(prompt, plan, santa, grinch_wins):
    class Story(BaseModel):
        story: str = Field(description="The story Santa and the Grinch")
    sys = "You are a game-master running a game where Santa tried to stop the Grinch from ruining Christmas. {grinch_goal} Meanwhile Santa had a plan to stop him. Given the plans of both the Grinch and Santa, briefly in a few paragraphs explain why Santa was ultimately successful in thwarting the Grinch"
    if grinch_wins:
        sys = "You are a game-master running a game where Santa tried to stop the Grinch from ruining Christmas. {grinch_goal} Meanwhile Santa had a plan to stop him. Given the plans of both the Grinch and Santa, briefly in a few paragraphs explain why Santa was ultimately unsuccessful in thwarting the Grinch"
    why_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            sys
        ),
        (
            "user",
            "The Grinch's Goal: {grinch_goal}\nHis plan:\n1. {p1}\n 2. {p2}\n 3. {p3}",
        ),
        (
            "user",
            "Santa's Plan: {santa_plan}"
        )
    ])
    model = ChatAnthropic(model="claude-3-5-sonnet-20240620").with_structured_output(Story)
    r = (why_prompt | model).invoke(
        {
            "grinch_goal": prompt.format(player="The Grinch"),
            "p1": plan[0],
            "p2": plan[1],
            "p3": plan[2],
            "santa_plan": santa
        }
    )
    print(r)
    return r.story

    

class GrinchSuccess(BaseModel):
    """If the grinch succeeds at his plan or not"""
    success: bool = Field(description="The success of the Grinch")
success_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a game-master running a game where Santa is trying to stop the Grinch from ruining Christmas. {grinch_goal} Meanwhile Santa has a plan to stop him. Given the plans of both the Grinch and Santa determine if the Grinch's plan is successful or if he gets thwarted by Santa."
    ),
    (
        "user",
        "The Grinch's Goal: {grinch_goal}\nHis plan:\n1. {p1}\n 2. {p2}\n 3. {p3}",
    ),
    (
        "user",
        "Santa's Plan: {santa_plan}"
    )
])
def does_grinch_succeed(prompt, plan, santa):
    model = ChatAnthropic(model="claude-3-5-sonnet-20240620").with_structured_output(GrinchSuccess)
    r = (success_prompt | model).invoke(
        {
            "grinch_goal": prompt.format(player="The Grinch"),
            "p1": plan[0],
            "p2": plan[1],
            "p3": plan[2],
            "santa_plan": santa
        }
    )
    return r.success

class GrinchPlausable(BaseModel):
    """If the grinch has a decent plan"""
    # why: str = Field(description="Why it's creative or not")
    is_plausable_specific_creative_plan: bool = Field(description="If the Grinch's plan could plausably work, is specific to his goal, and shows some creativity")

def is_grinch_plausable(prompt, plan):
    grinch_plausable_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a game-master running a game where Santa is trying to stop the Grinch from ruining Christmas. {grinch_goal} Is it possible for the Grinch's plan to succeed with at least 20% probability, is it specifc to his goal, and is it at least somewhat creative?"
        ),
        (
            "user",
            "His plan:\n1. {p1}\n 2. {p2}\n 3. {p3}",
        )
    ])
    model = ChatAnthropic(model="claude-3-5-sonnet-20240620").with_structured_output(GrinchPlausable)
    r = (grinch_plausable_prompt | model).invoke(
        {
            "grinch_goal": prompt.format(player="The Grinch"),
            "p1": plan[0],
            "p2": plan[1],
            "p3": plan[2],
        }
    )
    # print(r)
    return r.is_plausable_specific_creative_plan

class SantaPlausable(BaseModel):
    """If Santa has a decent plan"""
    # why: str = Field(description="Why")
    is_plausable_specific_creative_plan: bool = Field(description="If Santa's plan to stop the Grinch could plausably work, is specific to his goal")
def is_santa_plausable(prompt, plan, santa):
    santa_plausable_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a game-master running a game where Santa is trying to stop the Grinch from ruining Christmas. {grinch_goal} Santa has a plan for trying to stop him. Is it possible for Santa's plan to stop the Grinch's plan to succeed with at least 20% probability, and is it specifc to the Grinch's plan?"
        ),
        (
            "user",
            "The Grinch's plan:\n1. {p1}\n 2. {p2}\n 3. {p3}",
        ),
        (
            "user",
            "Santa's plan:\n{santa_plan}",
        )
    ])
    model = ChatAnthropic(model="claude-3-5-sonnet-20240620").with_structured_output(SantaPlausable)
    r = (santa_plausable_prompt | model).invoke(
        {
            "grinch_goal": prompt.format(player="The Grinch"),
            "p1": plan[0],
            "p2": plan[1],
            "p3": plan[2],
            "santa_plan": santa
        }
    )
    # print(r)
    return r.is_plausable_specific_creative_plan

if __name__ == "__main__":
    prompt = random.choice(initial_prompts)
    print(f"Grinch prompt: {prompt}")
    print("Three step plan:")
    plan = [
        input("1. "),
        input("2. "),
        input("3. "),
    ]
    print(elves(prompt, plan))
    santa = input("Santa's plan: ")
    r = eval(prompt, plan, santa)
    print(why(prompt, plan, santa, r))