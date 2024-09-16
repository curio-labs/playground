from django.http import JsonResponse


class ActionView:
    def post(self, request, action):
        if action == "save":
            return self.save(request)
        elif action == "run":
            return self.run(request)
        elif action == "output":
            return self.output(request)
        elif action == "re-run":
            return self.rerun(request)
        else:
            return JsonResponse({"error": "Invalid action"}, status=400)

    def save(self, request):
        raise NotImplementedError("Method save not implemented")

    def run(self, request):
        raise NotImplementedError("Method run not implemented")

    def output(self, request):
        raise NotImplementedError("Method output not implemented")

    def rerun(self, request):
        pass
