from django.conf import settings

from content_location.models import ContentLocation
from transaction.models import Transaction
from inbox.models import Inbox, Member as InboxMember, Content as InboxContent
from progress.models import ProgressSlotContent
from log.models import Content as LogContent
from instructor.models import Account as InstructorAccount
from provider.models import Account as ProviderAccount


def get_slot_by_progress_event(progress_event):
    event_id = progress_event.content_id
    account_id = progress_event.account_id
    is_standalone = Transaction.objects.filter(
        content_type_id=settings.CONTENT_TYPE('event.event').id,
        content_id=event_id,
        account_id=account_id
    ).exists()

    if is_standalone:
        return None

    regenerator = RegenerateInbox()
    _data_dict = regenerator.get_data_dict(event_id)
    transaction = Transaction.objects.filter(
        content_type_id=settings.CONTENT_TYPE('learning_path.learningpath').id,
        content_id__in=_data_dict.keys(),
        account_id=account_id,
    ).order_by('-datetime_create').first()

    if transaction is None:
        raise Exception('Why Not Found transaction!!!!!')

    slot_id = _data_dict.get(transaction.content_id)
    if slot_id is None:
        raise Exception('Why Not Found transaction!!!!!')
    return slot_id


class RegenerateInbox:
    data_event_dict = {}

    def make_event_map_slot(self, event_id):
        _data_dict = {}
        learning_path_event_slot_list = list(ContentLocation.objects.filter(
            content_type=settings.CONTENT_TYPE('event.event').id,
            content_id=event_id,
            parent1_content_type_id=settings.CONTENT_TYPE('learning_path.learningpath').id,
            parent3_content_type_id=settings.CONTENT_TYPE('slot.slot').id
        ).extra(select={'learning_path_id': 'parent1_content_id', 'slot_id': 'parent3_content_id'}
                ).values('learning_path_id', 'slot_id'))
        learning_path_event_slot_dict = {x['learning_path_id']: x['slot_id'] for x in
                                         learning_path_event_slot_list}

        _data_dict.update(learning_path_event_slot_dict)
        learning_path_event_program_list = list(ProgressSlotContent.objects.filter(
            parent_content_type=settings.CONTENT_TYPE('learning_path.learningpath'),
            content_type=settings.CONTENT_TYPE('event.event'),
            content_id=event_id
        ).extra(select={'learning_path_id': 'parent_content_id', 'slot_id': 'slot_id'}
                ).values('learning_path_id', 'slot_id'))
        learning_path_event_program_dict = {
            x['learning_path_id']: x['slot_id'] for x in learning_path_event_program_list
        }
        _data_dict.update(learning_path_event_program_dict)
        return _data_dict

    def get_data_dict(self, event_id):
        data = self.data_event_dict.get(event_id, None)
        if data is not None:
            return data
        _data_dict = self.make_event_map_slot(event_id)
        self.data_event_dict[event_id] = _data_dict
        return _data_dict

    def execute(self, progress_event):
        event_id = progress_event.content_id
        account_id = progress_event.account_id
        inbox_content = InboxContent.objects.filter(
            inbox__type=11,
            content_type_id=settings.CONTENT_TYPE('event.event').id,
        ).select_related('inbox').first()
        if inbox_content is None:
            return None
        inbox = inbox_content.inbox
        inbox_member = InboxMember.objects.filter(
            inbox_id=inbox.id,
            account_id=account_id
        ).select_related('inbox').first()

        is_standalone = Transaction.objects.filter(
            content_type_id=settings.CONTENT_TYPE('event.event').id,
            content_id=event_id,
            account_id=account_id
        ).exists()
        if is_standalone:
            if inbox.slot_id is None:
                return None
            inbox.slot_id = None
            return inbox
        _data_dict = self.get_data_dict(event_id)
        transaction = Transaction.objects.filter(
            content_type_id=settings.CONTENT_TYPE('learning_path.learningpath').id,
            content_id__in=_data_dict.keys(),
            account_id=account_id,
        ).order_by('-datetime_create').first()
        if transaction is None:
            return
        slot_id = _data_dict.get(transaction.content_id)
        if slot_id is not None:
            inbox.slot_id = slot_id
            return inbox
        return None


def get_dashboard_receive_account_id_list(content_type_id, content_id, sender_account_id=-1):
    # content_creator
    content_creator_account_id_set = set(LogContent.objects.filter(
        content_id=content_id,
        content_type_id=content_type_id,
        action_code='CONTENT_CREATED').distinct().values_list('account_id', flat=True))

    provider_account_id_set = set(ProviderAccount.objects.filter(
        provider__content__content_type_id=content_type_id,
        provider__content__content_id=content_id).distinct().values_list('account_id', flat=True))

    instructor_account_id_set = set(InstructorAccount.objects.filter(
        instructor__content__content_type_id=content_type_id,
        instructor__content__content_id=content_id).distinct().values_list('account_id', flat=True))

    account_id_list = list(provider_account_id_set.union(instructor_account_id_set).union(content_creator_account_id_set))
    # if sender_account_id in account_id_list:
    #     account_id_list.remove(sender_account_id)
    return account_id_list
